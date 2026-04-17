from services.orchestrator.analyzer import analyze_request


def _hosts() -> list[dict]:
    return [
        {'hostname': 'ol9server1', 'ip': '192.168.250.30'},
        {'hostname': 'rocky9server1', 'ip': '192.168.250.40'},
    ]


def test_analyzer_create_user() -> None:
    result = analyze_request('Crear usuario pedro en ol9server1 sin sudo', _hosts())

    assert result.spec['request_type'] == 'create_user'
    assert result.spec['params']['username'] == 'pedro'
    assert result.spec['targets'] == ['ol9server1']


def test_analyzer_delete_user() -> None:
    result = analyze_request('Eliminar usuario legacy01 en ol9server1', _hosts())

    assert result.spec['request_type'] == 'delete_user'
    assert result.spec['params']['username'] == 'legacy01'


def test_analyzer_add_ssh_key_default() -> None:
    result = analyze_request('Agregar clave SSH al usuario analista en ol9server1', _hosts())

    assert result.spec['request_type'] == 'add_ssh_key'
    assert result.spec['params']['username'] == 'analista'
    assert result.spec['params']['ssh_public_key'].startswith('ssh-ed25519 ')
    assert any('llave demo' in warning for warning in result.warnings)


def test_analyzer_create_directory() -> None:
    result = analyze_request('Crear carpeta /opt/automation_factory_lite/jobs/demo en rocky9server1', _hosts())

    assert result.spec['request_type'] == 'create_directory'
    assert result.spec['params']['directory_path'] == '/opt/automation_factory_lite/jobs/demo'
    assert result.spec['targets'] == ['rocky9server1']


def test_analyzer_service_install() -> None:
    result = analyze_request('Install nginx on rocky9server1', _hosts())

    assert result.spec['request_type'] == 'install_service'
    assert result.spec['params']['service_name'] == 'nginx'


def test_analyzer_install_package() -> None:
    result = analyze_request('Instalar paquete jq en rocky9server1', _hosts())

    assert result.spec['request_type'] == 'install_package'
    assert result.spec['params']['package_name'] == 'jq'


def test_analyzer_restart_service() -> None:
    result = analyze_request('Reiniciar servicio nginx en rocky9server1', _hosts())

    assert result.spec['request_type'] == 'restart_service'
    assert result.spec['params']['service_name'] == 'nginx'


def test_analyzer_agent_default_cockpit() -> None:
    result = analyze_request('Instalar agente en ol9server1', _hosts())

    assert result.spec['request_type'] == 'install_agent'
    assert result.spec['params']['agent_name'] == 'cockpit'
    assert any('cockpit' in warning for warning in result.warnings)


def test_analyzer_connectivity_target() -> None:
    result = analyze_request('Chequeo de conectividad a 8.8.4.4 desde ol9server1', _hosts())

    assert result.spec['request_type'] == 'check_connectivity'
    assert result.spec['params']['connectivity_target'] == '8.8.4.4'
