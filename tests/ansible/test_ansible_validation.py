from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS = ROOT / 'ansible' / 'playbooks'
LOCAL_TMP = ROOT / '.ansible-tmp'
LOCAL_TMP.mkdir(parents=True, exist_ok=True)
CACHE_TMP = ROOT / '.cache'
CACHE_TMP.mkdir(parents=True, exist_ok=True)
ANSIBLE_HOME = ROOT / '.ansible-home'
ANSIBLE_HOME.mkdir(parents=True, exist_ok=True)
USER_HOME = os.environ.get('HOME', '/home/ansible')
USER_LOCAL_BIN = str(Path(USER_HOME) / '.local' / 'bin')

TEST_ENV = os.environ.copy()
TEST_ENV.update(
    {
        'ANSIBLE_LOCAL_TEMP': str(LOCAL_TMP),
        'ANSIBLE_REMOTE_TMP': str(LOCAL_TMP),
        # Keep real HOME so user-site ansible packages remain importable.
        'HOME': USER_HOME,
        'PATH': f"{USER_LOCAL_BIN}:{TEST_ENV.get('PATH', '')}",
        'XDG_CACHE_HOME': str(CACHE_TMP),
        'ANSIBLE_HOME': str(ANSIBLE_HOME),
        'ANSIBLE_GALAXY_CACHE_DIR': str(ANSIBLE_HOME / 'galaxy_cache'),
    }
)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT / 'ansible', env=TEST_ENV, text=True, capture_output=True, check=False)


def _tool_ready(tool: str) -> bool:
    if shutil.which(tool) is None:
        return False
    check = subprocess.run([tool, '--version'], env=TEST_ENV, text=True, capture_output=True, check=False)
    return check.returncode == 0


@pytest.mark.parametrize(
    'playbook',
    [
        'create_user.yml',
        'delete_user.yml',
        'reset_password.yml',
        'add_ssh_key.yml',
        'create_directory.yml',
        'install_service.yml',
        'install_package.yml',
        'restart_service.yml',
        'manage_service.yml',
        'install_agent.yml',
        'deploy_template.yml',
        'check_uptime.yml',
        'check_patch_status.yml',
        'check_connectivity.yml',
    ],
)
def test_ansible_syntax_check(playbook: str) -> None:
    if not _tool_ready('ansible-playbook'):
        pytest.skip('ansible-playbook not fully available in environment')
    res = _run(['ansible-playbook', '-i', 'inventories/lab.ini', '--syntax-check', f'playbooks/{playbook}'])
    assert res.returncode == 0, res.stderr


def test_ansible_lint_if_available() -> None:
    if not _tool_ready('ansible-lint'):
        pytest.skip('ansible-lint not fully available in environment')
    res = subprocess.run(
        ['ansible-lint', 'ansible/playbooks'],
        cwd=ROOT,
        env=TEST_ENV,
        text=True,
        capture_output=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_yamllint_if_available() -> None:
    if not _tool_ready('yamllint'):
        pytest.skip('yamllint not fully available in environment')
    res = subprocess.run(['yamllint', 'ansible'], cwd=ROOT, env=TEST_ENV, text=True, capture_output=True, check=False)
    assert res.returncode == 0, res.stdout + res.stderr
