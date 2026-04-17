from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ApprovalDecision,
    AuditLog,
    AutomationRequest,
    ExecutionRecord,
    TimelineEvent,
)
from services.automation_catalog.service import find_reusable_automation, upsert_generated_automation
from services.awx_client.client import build_awx_client
from services.cmdb_sim.service import list_hosts, validate_targets
from services.orchestrator.analyzer import analyze_request
from services.playbook_factory.factory import generate_from_blueprint
from services.policy_engine.service import PolicyDecision, classify_risk

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except Exception:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = 'END'


class OrchestratorState(TypedDict, total=False):
    db: Session
    request: AutomationRequest
    spec: dict
    warnings: list[str]
    host_context: list[dict]
    validation_context: dict
    policy: PolicyDecision
    automation: Any
    execution: Any
    rejected: bool
    rejection_reason: Any


@dataclass
class OrchestratorConfig:
    root_dir: str
    settings: Any


class AutomationOrchestrator:
    def __init__(self, config: OrchestratorConfig) -> None:
        self.config = config
        enable_langgraph = bool(getattr(config.settings, 'enable_langgraph', False))
        self.graph = self._build_graph() if (LANGGRAPH_AVAILABLE and enable_langgraph) else None

    def _event(self, db: Session, request_id: str, actor: str, step: str, status: str, payload: dict) -> None:
        db.add(
            TimelineEvent(
                request_id=request_id,
                actor=actor,
                step=step,
                status=status,
                payload=payload,
            )
        )

    def _audit(self, db: Session, request_id: str | None, event_type: str, message: str, payload: dict) -> None:
        db.add(AuditLog(request_id=request_id, event_type=event_type, message=message, payload=payload))

    def _build_graph(self):
        graph = StateGraph(OrchestratorState)
        graph.add_node('analyze', self._node_analyze)
        graph.add_node('build', self._node_build)
        graph.add_node('review', self._node_review)
        graph.add_node('publish_execute', self._node_publish_execute)

        graph.set_entry_point('analyze')
        graph.add_edge('analyze', 'build')
        graph.add_edge('build', 'review')
        graph.add_edge('review', 'publish_execute')
        graph.add_edge('publish_execute', END)
        return graph.compile()

    def _node_analyze(self, state: OrchestratorState) -> OrchestratorState:
        db = state['db']
        req = state['request']
        known_hosts = [
            {
                'hostname': h.hostname,
                'ip': h.ip,
                'environment': h.environment,
                'criticality': h.criticality,
            }
            for h in list_hosts(db)
        ]

        analysis = analyze_request(req.raw_request, known_hosts)
        spec = analysis.spec
        warnings = analysis.warnings

        target_validation = validate_targets(db, spec.get('targets', []), spec.get('request_type', 'unsupported'))
        if target_validation.missing_targets:
            warnings.append(f"Targets no encontrados: {target_validation.missing_targets}")
        if target_validation.denied_targets:
            warnings.append(f"Targets sin permiso para acción solicitada: {target_validation.denied_targets}")

        host_context = [
            {
                'hostname': h.hostname,
                'ip': h.ip,
                'environment': h.environment,
                'criticality': h.criticality,
            }
            for h in target_validation.valid_hosts
        ]

        req.structured_spec = spec
        req.warnings = warnings
        req.status = 'analyzed'
        db.add(req)

        self._event(
            db,
            req.id,
            actor='Analista',
            step='interpret_request',
            status='ok',
            payload={'spec': spec, 'warnings': warnings},
        )

        return {
            **state,
            'spec': spec,
            'warnings': warnings,
            'host_context': host_context,
            'validation_context': {
                'missing_targets': target_validation.missing_targets,
                'denied_targets': target_validation.denied_targets,
            },
        }

    def _node_build(self, state: OrchestratorState) -> OrchestratorState:
        db = state['db']
        req = state['request']
        spec = state['spec']

        if spec.get('request_type') == 'unsupported':
            self._event(
                db,
                req.id,
                actor='Constructor',
                step='skip_generation',
                status='warn',
                payload={'reason': 'request_type unsupported'},
            )
            return state

        reused = find_reusable_automation(db, spec)
        if reused:
            req.automation_id = reused.id
            req.status = 'automation_reused'
            db.add(req)
            self._event(
                db,
                req.id,
                actor='Constructor',
                step='reuse_automation',
                status='ok',
                payload={'automation_id': reused.id, 'name': reused.name},
            )
            return {**state, 'automation': reused}

        try:
            artifact = generate_from_blueprint(spec, self.config.root_dir)
            entry = upsert_generated_automation(
                db,
                name=artifact.name,
                request_type=spec['request_type'],
                playbook_path=os.path.relpath(artifact.playbook_path, Path(self.config.root_dir) / 'ansible'),
                required_params=artifact.required_params,
                optional_params=artifact.optional_params,
                risk_level='low',
                validation_results=artifact.validation_results,
                metadata={
                    'vars_path': artifact.vars_path,
                    'readme_path': artifact.readme_path,
                    'metadata_path': artifact.metadata_path,
                },
                origin='generated',
            )
            req.automation_id = entry.id
            req.status = 'automation_generated'
            db.add(req)
            self._event(
                db,
                req.id,
                actor='Constructor',
                step='generate_blueprint_automation',
                status='ok',
                payload={
                    'automation_id': entry.id,
                    'name': entry.name,
                    'playbook_path': entry.playbook_path,
                    'validation_results': artifact.validation_results,
                },
            )
            return {**state, 'automation': entry}
        except Exception as exc:
            reason = f'Error de generación segura: {exc}'
            self._event(
                db,
                req.id,
                actor='Constructor',
                step='generate_blueprint_automation',
                status='error',
                payload={'error': reason},
            )
            return {**state, 'rejected': True, 'rejection_reason': reason}

    def _node_review(self, state: OrchestratorState) -> OrchestratorState:
        db = state['db']
        req = state['request']
        spec = state['spec']

        if state.get('rejected'):
            req.status = 'rejected'
            req.risk_level = 'high'
            req.risk_reason = state.get('rejection_reason')
            req.rejection_reason = state.get('rejection_reason')
            db.add(req)
            self._event(
                db,
                req.id,
                actor='Revisor/Publicador',
                step='review_rejected',
                status='error',
                payload={'reason': req.rejection_reason},
            )
            return state

        validation_context = state.get('validation_context', {})
        missing = validation_context.get('missing_targets', [])
        denied = validation_context.get('denied_targets', [])

        if missing or denied:
            req.status = 'rejected'
            req.risk_level = 'high'
            req.risk_reason = 'Hosts inválidos o no autorizados para acción solicitada.'
            req.rejection_reason = f'missing={missing}, denied={denied}'
            db.add(req)
            self._event(
                db,
                req.id,
                actor='Revisor/Publicador',
                step='validate_targets',
                status='error',
                payload={'missing': missing, 'denied': denied},
            )
            return {**state, 'rejected': True, 'rejection_reason': req.rejection_reason}

        decision = classify_risk(spec, state.get('host_context', []))

        req.risk_level = decision.risk_level
        req.risk_reason = decision.reason
        req.requires_approval = decision.requires_approval

        if not decision.allowed:
            req.status = 'rejected'
            req.rejection_reason = decision.reason
            db.add(req)
            self._event(
                db,
                req.id,
                actor='Revisor/Publicador',
                step='policy_gate',
                status='error',
                payload={'risk': decision.risk_level, 'reason': decision.reason},
            )
            return {**state, 'rejected': True, 'rejection_reason': decision.reason, 'policy': decision}

        if decision.requires_approval and not req.approved:
            req.status = 'pending_approval'
            db.add(req)
            pending = db.execute(select(ApprovalDecision).where(ApprovalDecision.request_id == req.id)).scalar_one_or_none()
            if not pending:
                db.add(ApprovalDecision(request_id=req.id, status='pending'))
            self._event(
                db,
                req.id,
                actor='Revisor/Publicador',
                step='policy_gate',
                status='needs_approval',
                payload={'risk': decision.risk_level, 'reason': decision.reason},
            )
            return {**state, 'policy': decision}

        req.status = 'validated'
        db.add(req)
        self._event(
            db,
            req.id,
            actor='Revisor/Publicador',
            step='policy_gate',
            status='ok',
            payload={'risk': decision.risk_level, 'reason': decision.reason},
        )
        return {**state, 'policy': decision}

    def _node_publish_execute(self, state: OrchestratorState) -> OrchestratorState:
        db = state['db']
        req = state['request']

        if req.status in {'rejected', 'pending_approval'}:
            self._audit(
                db,
                req.id,
                event_type='request_terminal',
                message=f'Request ended with status={req.status}',
                payload={'risk': req.risk_level, 'reason': req.risk_reason},
            )
            return state

        automation = state.get('automation')
        spec = state.get('spec') or {}
        targets = spec.get('targets') or []

        if automation is None:
            req.status = 'failed'
            req.rejection_reason = 'No automation was built or reused for execution.'
            db.add(req)
            self._event(
                db,
                req.id,
                actor='Revisor/Publicador',
                step='publish_execute',
                status='error',
                payload={'error': req.rejection_reason},
            )
            return {**state, 'rejected': True, 'rejection_reason': req.rejection_reason}

        awx_client = build_awx_client(self.config.settings)
        playbook_path = automation.playbook_path
        # Backward compatibility for older catalog entries seeded as `playbooks/...`.
        if isinstance(playbook_path, str) and playbook_path.startswith('playbooks/'):
            playbook_path = f'ansible/{playbook_path}'

        try:
            awx_client.publish_job_template(
                name=automation.name,
                playbook_path=playbook_path,
                inventory_name=self.config.settings.awx_inventory,
            )
            launch = awx_client.launch_job(
                template_name=automation.name,
                limit_hosts=targets,
                extra_vars=spec.get('params', {}),
            )

            execution = ExecutionRecord(
                request_id=req.id,
                awx_mode=launch.mode,
                template_name=launch.template_name,
                hosts=targets,
                extra_vars=spec.get('params', {}),
                job_id=launch.job_id,
                status=launch.status,
                output_summary=launch.summary,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            db.add(execution)
            db.flush()

            req.execution_id = execution.id
            req.status = 'executed' if launch.status in {'successful', 'launched'} else 'failed'
            db.add(req)

            self._event(
                db,
                req.id,
                actor='Revisor/Publicador',
                step='publish_execute',
                status='ok',
                payload={'awx_mode': launch.mode, 'job_id': launch.job_id, 'status': launch.status},
            )
            self._audit(
                db,
                req.id,
                event_type='execution',
                message='Execution completed via AWX client.',
                payload={'mode': launch.mode, 'job_id': launch.job_id, 'status': launch.status},
            )
            return {**state, 'execution': execution}
        except Exception as exc:
            req.status = 'failed'
            req.rejection_reason = str(exc)
            db.add(req)
            self._event(
                db,
                req.id,
                actor='Revisor/Publicador',
                step='publish_execute',
                status='error',
                payload={'error': str(exc)},
            )
            self._audit(
                db,
                req.id,
                event_type='execution_failure',
                message='Execution failed.',
                payload={'error': str(exc)},
            )
            return {**state, 'rejected': True, 'rejection_reason': str(exc)}

    def process_request(self, db: Session, request: AutomationRequest) -> AutomationRequest:
        state: OrchestratorState = {'db': db, 'request': request}

        if self.graph is not None:
            result = self.graph.invoke(state)
        else:
            result = self._node_analyze(state)
            result = self._node_build(result)
            result = self._node_review(result)
            result = self._node_publish_execute(result)

        db.commit()
        db.refresh(request)
        return request

    def resume_after_approval(self, db: Session, request: AutomationRequest) -> AutomationRequest:
        if not request.approved:
            return request

        spec = request.structured_spec or {}
        automation = None
        if request.automation_id:
            from app.models import AutomationCatalogEntry

            automation = db.execute(
                select(AutomationCatalogEntry).where(AutomationCatalogEntry.id == request.automation_id)
            ).scalar_one_or_none()

        state: OrchestratorState = {
            'db': db,
            'request': request,
            'spec': spec,
            'automation': automation,
            'host_context': [],
            'validation_context': {'missing_targets': [], 'denied_targets': []},
        }

        state = self._node_review(state)
        state = self._node_publish_execute(state)

        db.commit()
        db.refresh(request)
        return request
