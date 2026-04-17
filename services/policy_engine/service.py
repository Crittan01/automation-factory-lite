from __future__ import annotations

from dataclasses import dataclass

FORBIDDEN_KEYWORDS = [
    'firewall',
    'sudoers',
    'kernel',
    'iptables',
    'network',
    'secret',
    'database',
    'upgrade',
    'massive update',
]

SUPPORTED_ACTIONS = {
    'create_user',
    'install_service',
    'manage_service',
    'install_agent',
    'deploy_template',
}


@dataclass
class PolicyDecision:
    risk_level: str
    reason: str
    requires_approval: bool
    allowed: bool


def classify_risk(spec: dict, host_context: list[dict]) -> PolicyDecision:
    raw = (spec.get('raw_text') or '').lower()
    request_type = spec.get('request_type', '')
    params = spec.get('params', {})

    if any(keyword in raw for keyword in FORBIDDEN_KEYWORDS):
        return PolicyDecision(
            risk_level='high',
            reason='La solicitud contiene una acción fuera de política de seguridad.',
            requires_approval=False,
            allowed=False,
        )

    if request_type not in SUPPORTED_ACTIONS:
        return PolicyDecision(
            risk_level='high',
            reason='Tipo de automatización fuera del catálogo permitido V1.',
            requires_approval=False,
            allowed=False,
        )

    environments = {h.get('environment', 'dev') for h in host_context}
    criticalities = {h.get('criticality', 'medium') for h in host_context}

    if request_type == 'manage_service' and params.get('state') in {'stop', 'restart'}:
        return PolicyDecision(
            risk_level='medium',
            reason='Acción de impacto operativo (stop/restart) requiere aprobación.',
            requires_approval=True,
            allowed=True,
        )

    if request_type == 'install_agent' and len(spec.get('targets', [])) > 1:
        return PolicyDecision(
            risk_level='medium',
            reason='Instalación de agente en múltiples hosts requiere aprobación.',
            requires_approval=True,
            allowed=True,
        )

    if 'prod' in environments or 'high' in criticalities:
        return PolicyDecision(
            risk_level='medium',
            reason='Cambio en host productivo/alto impacto requiere aprobación.',
            requires_approval=True,
            allowed=True,
        )

    return PolicyDecision(
        risk_level='low',
        reason='Acción de bajo riesgo dentro de catálogo y políticas.',
        requires_approval=False,
        allowed=True,
    )
