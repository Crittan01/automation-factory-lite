from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ServiceNowCase, ServiceNowCaseEvent
from services.policy_engine.service import SUPPORTED_ACTIONS

OPEN_CASE_STATES = {'new', 'open', 'reopened'}


def _next_case_number(db: Session) -> str:
    latest = db.execute(select(ServiceNowCase).order_by(ServiceNowCase.created_at.desc())).scalars().first()
    if latest is None:
        return 'INC000001'
    digits = ''.join(ch for ch in latest.number if ch.isdigit())
    seq = int(digits) + 1 if digits else 1
    return f'INC{seq:06d}'


def list_cases(
    db: Session,
    *,
    state: str | None = None,
    assignment_group: str | None = None,
    limit: int = 200,
) -> list[ServiceNowCase]:
    query = select(ServiceNowCase).order_by(ServiceNowCase.updated_at.desc())
    if state:
        query = query.where(ServiceNowCase.state == state)
    if assignment_group:
        query = query.where(ServiceNowCase.assignment_group == assignment_group)
    return db.execute(query.limit(limit)).scalars().all()


def list_open_cases(db: Session, *, limit: int = 100) -> list[ServiceNowCase]:
    query = (
        select(ServiceNowCase)
        .where(ServiceNowCase.state.in_(list(OPEN_CASE_STATES)))
        .order_by(ServiceNowCase.created_at.asc())
        .limit(limit)
    )
    return db.execute(query).scalars().all()


def get_case_by_number(db: Session, case_number: str) -> ServiceNowCase | None:
    return db.execute(select(ServiceNowCase).where(ServiceNowCase.number == case_number)).scalar_one_or_none()


def list_case_events(db: Session, case_id: str) -> list[ServiceNowCaseEvent]:
    return db.execute(
        select(ServiceNowCaseEvent)
        .where(ServiceNowCaseEvent.case_id == case_id)
        .order_by(ServiceNowCaseEvent.created_at.asc())
    ).scalars().all()


def add_case_event(
    db: Session,
    *,
    case: ServiceNowCase,
    actor: str,
    event_type: str,
    message: str,
    payload: dict | None = None,
) -> ServiceNowCaseEvent:
    event = ServiceNowCaseEvent(
        case_id=case.id,
        actor=actor,
        event_type=event_type,
        message=message,
        payload=payload or {},
    )
    db.add(event)
    return event


def create_case(
    db: Session,
    *,
    short_description: str,
    description: str | None = None,
    request_type: str | None = None,
    params: dict | None = None,
    targets: list[str] | None = None,
    priority: str = '3',
    assignment_group: str = 'automation.factory',
    requested_by: str = 'servicenow.user',
    state: str = 'new',
) -> ServiceNowCase:
    case = ServiceNowCase(
        number=_next_case_number(db),
        short_description=short_description,
        description=description,
        request_type=request_type,
        params=params or {},
        targets=targets or [],
        priority=priority,
        assignment_group=assignment_group,
        requested_by=requested_by,
        state=state,
    )
    db.add(case)
    db.flush()
    add_case_event(
        db,
        case=case,
        actor='servicenow_sim',
        event_type='case_created',
        message='Case created in ServiceNow simulation.',
        payload={'request_type': request_type, 'targets': targets or []},
    )
    db.commit()
    db.refresh(case)
    return case


def seed_demo_cases(db: Session, host_names: Iterable[str]) -> list[ServiceNowCase]:
    return _seed_demo_cases(db, host_names, force=False)


def _demo_payloads(hosts: list[str], *, suffix: str) -> list[dict]:
    host_1 = hosts[0]
    host_2 = hosts[1]
    return [
        {
            'short_description': f'Crear usuario analista_{suffix} en {host_1} sin sudo',
            'request_type': 'create_user',
            'params': {'username': f'analista_{suffix}'},
            'targets': [host_1],
            'priority': '3',
        },
        {
            'short_description': f'Eliminar usuario legacy_{suffix} en {host_1}',
            'request_type': 'delete_user',
            'params': {'username': f'legacy_{suffix}', 'remove_home': False},
            'targets': [host_1],
            'priority': '2',
        },
        {
            'short_description': f'Resetear contraseña de operador_{suffix} en {host_2}',
            'request_type': 'reset_password',
            'params': {
                'username': f'operador_{suffix}',
                'password_hash': '$6$aflite$nh5SmQK53WiA5WimFyNkJYpmzt3XQ2ZmW16CzXlI8rmSk8V4fHQ3h5DYvAs8N3Jf3R1lzcBuM6khj6R2lsWvY0',
            },
            'targets': [host_2],
            'priority': '2',
        },
        {
            'short_description': f'Añadir clave SSH a analista_{suffix} en {host_1}',
            'request_type': 'add_ssh_key',
            'params': {
                'username': f'analista_{suffix}',
                'ssh_public_key': f'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGu8wU6G48PWJ4QjzYYVQzq3Y7oC0etLJ9w3U5{suffix} demo@afl',
            },
            'targets': [host_1],
            'priority': '2',
        },
        {
            'short_description': f'Crear carpeta /opt/automation_factory_lite/jobs/{suffix} en {host_2}',
            'request_type': 'create_directory',
            'params': {'directory_path': f'/opt/automation_factory_lite/jobs/{suffix}'},
            'targets': [host_2],
            'priority': '3',
        },
        {
            'short_description': f'Reiniciar servicio nginx en {host_2}',
            'request_type': 'restart_service',
            'params': {'service_name': 'nginx'},
            'targets': [host_2],
            'priority': '2',
        },
        {
            'short_description': f'Instalar paquete jq en {host_1}',
            'request_type': 'install_package',
            'params': {'package_name': 'jq'},
            'targets': [host_1],
            'priority': '3',
        },
        {
            'short_description': f'Obtener uptime de {host_1}',
            'request_type': 'check_uptime',
            'params': {},
            'targets': [host_1],
            'priority': '4',
        },
        {
            'short_description': f'Verificar estado de parches en {host_2}',
            'request_type': 'check_patch_status',
            'params': {},
            'targets': [host_2],
            'priority': '4',
        },
        {
            'short_description': f'Chequeo de conectividad a 8.8.8.8 desde {host_1}',
            'request_type': 'check_connectivity',
            'params': {'connectivity_target': '8.8.8.8'},
            'targets': [host_1],
            'priority': '4',
        },
        {
            'short_description': f'Instalar agente cockpit en {host_1} y {host_2}',
            'request_type': 'install_agent',
            'params': {'agent_name': 'cockpit'},
            'targets': [host_1, host_2],
            'priority': '2',
        },
        {
            'short_description': f'Abrir firewall para puerto 8080 en {host_1}',
            'request_type': 'unsupported',
            'params': {'port': 8080},
            'targets': [host_1],
            'priority': '1',
        },
    ]


def _seed_demo_cases(db: Session, host_names: Iterable[str], *, force: bool) -> list[ServiceNowCase]:
    hosts = list(host_names)
    if len(hosts) < 2:
        return []

    if not force:
        existing_seed = db.execute(
            select(ServiceNowCase).where(ServiceNowCase.short_description.like('DEMO-SNOW%')).limit(1)
        ).scalar_one_or_none()
        if existing_seed:
            return []

    batch_tag = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    batch_prefix = f'DEMO-SNOW[{batch_tag}]' if force else 'DEMO-SNOW'
    suffix = batch_tag[-6:] if force else 'base'

    created: list[ServiceNowCase] = []
    for item in _demo_payloads(hosts, suffix=suffix):
        created.append(
            create_case(
                db,
                short_description=f"{batch_prefix}: {item['short_description']}",
                request_type=item['request_type'],
                params=item['params'],
                targets=item['targets'],
                priority=item['priority'],
                requested_by='snow.demo',
            )
        )
    return created


def seed_demo_cases_force(db: Session, host_names: Iterable[str]) -> list[ServiceNowCase]:
    return _seed_demo_cases(db, host_names, force=True)


def request_type_supported(request_type: str | None) -> bool:
    if request_type is None:
        return True
    return request_type in SUPPORTED_ACTIONS


def case_to_request_text(case: ServiceNowCase) -> str:
    if case.request_type == 'create_user':
        username = (case.params or {}).get('username', 'operador_demo')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Crear usuario {username} en {targets} sin sudo'
    if case.request_type == 'delete_user':
        username = (case.params or {}).get('username', 'operador_demo')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Eliminar usuario {username} en {targets}'
    if case.request_type == 'reset_password':
        username = (case.params or {}).get('username', 'operador_demo')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Resetear contraseña de usuario {username} en {targets}'
    if case.request_type == 'add_ssh_key':
        username = (case.params or {}).get('username', 'operador_demo')
        key = (case.params or {}).get('ssh_public_key', '')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Agregar clave SSH "{key}" al usuario {username} en {targets}'
    if case.request_type == 'create_directory':
        directory_path = (case.params or {}).get('directory_path', '/opt/automation_factory_lite/work')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Crear carpeta {directory_path} en {targets}'
    if case.request_type == 'install_service':
        service_name = (case.params or {}).get('service_name', 'nginx')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Instalar {service_name} en {targets}'
    if case.request_type == 'install_package':
        package_name = (case.params or {}).get('package_name', 'jq')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Instalar paquete {package_name} en {targets}'
    if case.request_type == 'restart_service':
        service_name = (case.params or {}).get('service_name', 'nginx')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Reiniciar servicio {service_name} en {targets}'
    if case.request_type == 'manage_service':
        service_name = (case.params or {}).get('service_name', 'nginx')
        state = (case.params or {}).get('state', 'start')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'{state} {service_name} en {targets}'
    if case.request_type == 'install_agent':
        agent_name = (case.params or {}).get('agent_name', 'cockpit')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Instalar agente {agent_name} en {targets}'
    if case.request_type == 'deploy_template':
        destination_path = (case.params or {}).get('destination_path', '/etc/nginx/conf.d/service.conf')
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Desplegar plantilla segura en {destination_path} para {targets}'
    if case.request_type == 'check_uptime':
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Obtener uptime en {targets}'
    if case.request_type == 'check_patch_status':
        targets = ' y '.join(case.targets or ['ol9server1'])
        return f'Verificar estado de parches en {targets}'
    if case.request_type == 'check_connectivity':
        target = (case.params or {}).get('connectivity_target', '8.8.8.8')
        hosts = ' y '.join(case.targets or ['ol9server1'])
        return f'Chequeo de conectividad a {target} desde {hosts}'
    return case.short_description


def mark_case_manual_attention(db: Session, case: ServiceNowCase, reason: str) -> None:
    case.state = 'needs_manual_attention'
    case.last_agent_run_at = datetime.utcnow()
    case.resolution_notes = reason
    db.add(case)
    add_case_event(
        db,
        case=case,
        actor='snow_agent',
        event_type='manual_attention_required',
        message='Case requires manual follow-up.',
        payload={'reason': reason},
    )
