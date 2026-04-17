from services.orchestrator.analyzer import analyze_request


def test_analyzer_create_user() -> None:
    hosts = [{'hostname': 'ol9server1', 'ip': '192.168.250.30'}]
    result = analyze_request('Crear usuario pedro en ol9server1 sin sudo', hosts)

    assert result.spec['request_type'] == 'create_user'
    assert result.spec['params']['username'] == 'pedro'
    assert result.spec['targets'] == ['ol9server1']


def test_analyzer_service_install() -> None:
    hosts = [{'hostname': 'rocky9server1', 'ip': '192.168.250.40'}]
    result = analyze_request('Install nginx on rocky9server1', hosts)

    assert result.spec['request_type'] == 'install_service'
    assert result.spec['params']['service_name'] == 'nginx'
