from services.policy_engine.service import classify_risk


def test_policy_low_risk() -> None:
    spec = {
        'raw_text': 'crear usuario',
        'request_type': 'create_user',
        'params': {'username': 'alice'},
        'targets': ['ol9server1'],
    }
    hosts = [{'environment': 'dev', 'criticality': 'medium'}]
    decision = classify_risk(spec, hosts)

    assert decision.allowed is True
    assert decision.risk_level == 'low'


def test_policy_medium_risk_for_multi_host_agent() -> None:
    spec = {
        'raw_text': 'instalar agente',
        'request_type': 'install_agent',
        'params': {'agent_name': 'cockpit'},
        'targets': ['ol9server1', 'rocky9server1'],
    }
    hosts = [{'environment': 'dev', 'criticality': 'medium'}]
    decision = classify_risk(spec, hosts)

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.risk_level == 'medium'


def test_policy_medium_for_identity_change() -> None:
    spec = {
        'raw_text': 'eliminar usuario',
        'request_type': 'delete_user',
        'params': {'username': 'legacy'},
        'targets': ['ol9server1'],
    }
    hosts = [{'environment': 'dev', 'criticality': 'medium'}]
    decision = classify_risk(spec, hosts)

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.risk_level == 'medium'


def test_policy_low_for_diagnostics() -> None:
    spec = {
        'raw_text': 'obtener uptime',
        'request_type': 'check_uptime',
        'params': {},
        'targets': ['ol9server1'],
    }
    hosts = [{'environment': 'dev', 'criticality': 'medium'}]
    decision = classify_risk(spec, hosts)

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.risk_level == 'low'


def test_policy_reject_forbidden() -> None:
    spec = {
        'raw_text': 'actualizar firewall del host',
        'request_type': 'manage_service',
        'params': {'service_name': 'nginx', 'state': 'start'},
        'targets': ['ol9server1'],
    }
    hosts = [{'environment': 'dev', 'criticality': 'medium'}]
    decision = classify_risk(spec, hosts)

    assert decision.allowed is False
    assert decision.risk_level == 'high'
