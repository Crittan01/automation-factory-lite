from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from services.playbook_factory.blueprints import SAFE_BLUEPRINTS


@dataclass
class PlaybookArtifact:
    name: str
    playbook_path: str
    vars_path: str
    readme_path: str
    metadata_path: str
    required_params: list[str]
    optional_params: list[str]
    validation_results: dict


def _render_content(blueprint: dict, targets_pattern: str) -> str:
    return blueprint['template'].replace('{{ targets_pattern }}', targets_pattern)


def _yaml_scalar(value: object) -> str:
    # JSON scalars are valid YAML scalars and safely escape user-provided strings.
    return json.dumps(value, ensure_ascii=False)


def _validate_supported(spec: dict) -> tuple[bool, str]:
    request_type = spec.get('request_type')
    params = spec.get('params') or {}

    if request_type not in SAFE_BLUEPRINTS:
        return False, 'Request type out of secure blueprint catalog.'

    blueprint = SAFE_BLUEPRINTS[request_type]

    for req in blueprint.get('required', []):
        if req not in params:
            return False, f'Missing required parameter: {req}'

    if request_type in {'reset_password'}:
        password_hash = str(params.get('password_hash') or '')
        if not password_hash.startswith('$6$'):
            return False, 'password_hash must be SHA-512 crypt format ($6$...).'

    if request_type == 'add_ssh_key':
        ssh_key = str(params.get('ssh_public_key') or '')
        if not (ssh_key.startswith('ssh-rsa ') or ssh_key.startswith('ssh-ed25519 ')):
            return False, 'SSH key must start with ssh-rsa or ssh-ed25519.'

    if request_type == 'create_directory':
        destination = str(params.get('directory_path') or '')
        if not any(destination.startswith(path) for path in blueprint.get('allowed_paths', [])):
            return False, 'Directory path outside allow list.'

    if request_type in {'install_service', 'manage_service'}:
        service = params.get('service_name')
        if service not in blueprint.get('allowed_services', []):
            return False, 'Service not in allow list.'

    if request_type == 'restart_service':
        service = params.get('service_name')
        if service not in blueprint.get('allowed_services', []):
            return False, 'Service not in allow list for restart.'

    if request_type == 'install_package':
        package_name = params.get('package_name')
        if package_name not in blueprint.get('allowed_packages', []):
            return False, 'Package not in allow list.'

    if request_type == 'manage_service':
        state = params.get('state')
        mapped = {'start': 'started', 'stop': 'stopped', 'restart': 'restarted', 'status': 'started'}
        if state not in mapped:
            return False, 'Service state not allowed.'

    if request_type == 'install_agent':
        agent = params.get('agent_name')
        if agent not in blueprint.get('allowed_agents', []):
            return False, 'Agent not in allow list.'

    if request_type == 'deploy_template':
        destination = params.get('destination_path', '')
        if not any(destination.startswith(path) for path in blueprint.get('allowed_paths', [])):
            return False, 'Destination path outside allow list.'

    if request_type == 'check_connectivity':
        target = str(params.get('connectivity_target') or '').strip()
        if target == '':
            return False, 'connectivity_target is required.'

    return True, 'Blueprint validation passed.'


def generate_from_blueprint(spec: dict, root_dir: str) -> PlaybookArtifact:
    ok, message = _validate_supported(spec)
    if not ok:
        raise ValueError(message)

    request_type = spec['request_type']
    blueprint = SAFE_BLUEPRINTS[request_type]
    params = spec.get('params', {})

    slug = f"{request_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    out_dir = Path(root_dir) / 'ansible' / 'generated' / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = spec.get('targets') or ['all']
    targets_pattern = ':'.join(targets)

    playbook = _render_content(blueprint, targets_pattern)
    if request_type == 'manage_service':
        desired = {'start': 'started', 'stop': 'stopped', 'restart': 'restarted', 'status': 'started'}[params['state']]
        playbook = playbook.replace('{{ desired_state }}', desired)

    playbook_path = out_dir / 'playbook.yml'
    playbook_path.write_text(playbook, encoding='utf-8')

    vars_path = out_dir / 'vars.yml'
    vars_lines = ['---'] + [f"{k}: {_yaml_scalar(v)}" for k, v in params.items()]
    vars_path.write_text('\n'.join(vars_lines) + '\n', encoding='utf-8')

    readme_path = out_dir / 'README.md'
    readme_path.write_text(
        '\n'.join(
            [
                f"# {slug}",
                '',
                f"Generated secure automation for `{request_type}`.",
                '',
                '## Safety',
                '- Generated from approved blueprint only.',
                '- Idempotent Ansible modules only.',
                '- Out-of-catalog operations are rejected.',
            ]
        )
        + '\n',
        encoding='utf-8',
    )

    metadata_path = out_dir / 'metadata.yml'
    metadata_path.write_text(
        '\n'.join(
            [
                '---',
                f"name: {slug}",
                f"request_type: {request_type}",
                'version: 1.0.0',
                'origin: generated',
                f"required_params: {blueprint.get('required', [])}",
                f"optional_params: {blueprint.get('optional', [])}",
            ]
        )
        + '\n',
        encoding='utf-8',
    )

    validation = {
        'blueprint_validation': message,
        'idempotent_modules_only': True,
        'catalog_restricted': True,
    }

    return PlaybookArtifact(
        name=slug,
        playbook_path=str(playbook_path),
        vars_path=str(vars_path),
        readme_path=str(readme_path),
        metadata_path=str(metadata_path),
        required_params=blueprint.get('required', []),
        optional_params=blueprint.get('optional', []),
        validation_results=validation,
    )
