import pytest

from services.playbook_factory.factory import generate_from_blueprint


def test_generate_create_directory_blueprint(tmp_path) -> None:
    (tmp_path / 'ansible').mkdir(parents=True, exist_ok=True)
    spec = {
        'request_type': 'create_directory',
        'params': {'directory_path': '/opt/automation_factory_lite/jobs/unit'},
        'targets': ['ol9server1'],
    }

    artifact = generate_from_blueprint(spec, str(tmp_path))
    assert artifact.name.startswith('create_directory-')
    assert (tmp_path / 'ansible' / 'generated').exists()
    assert 'playbook.yml' in artifact.playbook_path
    assert 'vars.yml' in artifact.vars_path


def test_reject_install_package_outside_allowlist() -> None:
    spec = {
        'request_type': 'install_package',
        'params': {'package_name': 'postgresql'},
        'targets': ['ol9server1'],
    }
    with pytest.raises(ValueError, match='allow list'):
        generate_from_blueprint(spec, '/tmp')


def test_generate_vars_escapes_double_quotes(tmp_path) -> None:
    (tmp_path / 'ansible').mkdir(parents=True, exist_ok=True)
    spec = {
        'request_type': 'add_ssh_key',
        'params': {
            'username': 'cert_user_01',
            'ssh_public_key': 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIdemoKey cert"@afl',
        },
        'targets': ['ol9server1'],
    }

    artifact = generate_from_blueprint(spec, str(tmp_path))
    vars_content = (tmp_path / artifact.vars_path).read_text(encoding='utf-8')
    assert '\\"' in vars_content
