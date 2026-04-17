from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    spec: dict
    warnings: list[str]


DEFAULT_PASSWORD_HASH = '$6$aflite$nh5SmQK53WiA5WimFyNkJYpmzt3XQ2ZmW16CzXlI8rmSk8V4fHQ3h5DYvAs8N3Jf3R1lzcBuM6khj6R2lsWvY0'
DEFAULT_SSH_KEY = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEEj9mmLsvrG8GoBc4q8FbUXKCO2VVXAIuFo3JxHl4aE afl-demo'
ALLOWED_SERVICES = ('nginx', 'httpd', 'cockpit')
ALLOWED_PACKAGES = ('jq', 'curl', 'git', 'rsync', 'htop', 'cockpit')


def _detect_targets(text: str, known_hosts: list[dict]) -> list[str]:
    lowered = text.lower()
    targets: list[str] = []

    if any(word in lowered for word in ['ambos', 'both', 'todos los hosts', 'all hosts']):
        return sorted({host['hostname'] for host in known_hosts})

    for host in known_hosts:
        if host['hostname'].lower() in lowered or host['ip'] in lowered:
            targets.append(host['hostname'])

    return sorted(set(targets))


def _extract_username(text: str) -> str | None:
    patterns = [
        r'(?:usuario|user)\s+([a-z_][a-z0-9_-]{1,31})',
        r'crear\s+([a-z_][a-z0-9_-]{1,31})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_unix_path(text: str) -> str | None:
    match = re.search(r'(/(?:[a-zA-Z0-9._-]+/?)+)', text)
    if not match:
        return None
    return match.group(1).rstrip('.,;')


def _extract_service_name(lowered: str) -> str | None:
    for service in ALLOWED_SERVICES:
        if service in lowered:
            return service
    return None


def _extract_package_name(lowered: str) -> str | None:
    for package in ALLOWED_PACKAGES:
        if package in lowered:
            return package
    return None


def _extract_password_hash(text: str) -> str | None:
    match = re.search(r'(\$6\$[^\s]+)', text)
    if not match:
        return None
    return match.group(1)


def _extract_ssh_key(text: str) -> str | None:
    match = re.search(r'(ssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/=]+(?:\s+[^\s]+)?)', text)
    if not match:
        return None
    return match.group(1).strip()


def _extract_connectivity_target(text: str, known_hosts: list[dict]) -> str | None:
    lowered = text.lower()
    hostnames = {host['hostname'].lower() for host in known_hosts}

    ip_match = re.search(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', text)
    if ip_match:
        candidate = ip_match.group(0)
        if candidate not in {host.get('ip') for host in known_hosts}:
            return candidate

    domain_match = re.search(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b', text)
    if domain_match:
        candidate = domain_match.group(0).lower()
        if candidate not in hostnames:
            return candidate

    phrase_match = re.search(r'(?:a|to)\s+([a-zA-Z0-9.-]+)', lowered)
    if phrase_match:
        candidate = phrase_match.group(1).strip('.,;')
        if candidate and candidate not in hostnames:
            return candidate

    return None


def analyze_request(text: str, known_hosts: list[dict]) -> AnalysisResult:
    lowered = text.lower()
    warnings: list[str] = []
    params: dict = {}
    request_type = 'unsupported'

    if ('crear' in lowered or 'create' in lowered) and ('usuario' in lowered or 'user' in lowered):
        request_type = 'create_user'
        username = _extract_username(text)
        if username:
            params['username'] = username
        else:
            params['username'] = 'operador_demo'
            warnings.append('No se detectó username, se aplicó default operador_demo.')

    elif ('eliminar' in lowered or 'borrar' in lowered or 'delete' in lowered) and ('usuario' in lowered or 'user' in lowered):
        request_type = 'delete_user'
        username = _extract_username(text)
        if username:
            params['username'] = username
        else:
            params['username'] = 'operador_demo'
            warnings.append('No se detectó username para eliminar, se aplicó default operador_demo.')

    elif any(word in lowered for word in ['resetear', 'restablecer', 'reset']) and any(
        word in lowered for word in ['password', 'contraseña', 'clave']
    ):
        request_type = 'reset_password'
        username = _extract_username(text)
        if username:
            params['username'] = username
        else:
            params['username'] = 'operador_demo'
            warnings.append('No se detectó username para reset de contraseña, se aplicó default operador_demo.')
        password_hash = _extract_password_hash(text)
        if password_hash:
            params['password_hash'] = password_hash
        else:
            params['password_hash'] = DEFAULT_PASSWORD_HASH
            warnings.append('No se detectó password hash, se aplicó hash demo seguro por default.')

    elif any(word in lowered for word in ['ssh', 'authorized_key', 'clave ssh']) and any(
        word in lowered for word in ['agregar', 'añadir', 'add']
    ):
        request_type = 'add_ssh_key'
        username = _extract_username(text)
        if username:
            params['username'] = username
        else:
            params['username'] = 'operador_demo'
            warnings.append('No se detectó username para clave SSH, se aplicó default operador_demo.')
        ssh_key = _extract_ssh_key(text)
        if ssh_key:
            params['ssh_public_key'] = ssh_key
        else:
            params['ssh_public_key'] = DEFAULT_SSH_KEY
            warnings.append('No se detectó clave SSH explícita, se aplicó llave demo por default.')

    elif ('instalar' in lowered or 'install' in lowered) and ('nginx' in lowered or 'httpd' in lowered):
        request_type = 'install_service'
        params['service_name'] = 'nginx' if 'nginx' in lowered else 'httpd'

    elif ('reiniciar' in lowered or 'restart' in lowered) and ('servicio' in lowered or 'service' in lowered):
        request_type = 'restart_service'
        service_name = _extract_service_name(lowered)
        if service_name:
            params['service_name'] = service_name
        else:
            params['service_name'] = 'nginx'
            warnings.append('No se detectó servicio explícito para restart, se aplicó nginx por default.')

    elif (
        any(keyword in lowered for keyword in ['start', 'stop', 'restart', 'status', 'iniciar', 'detener', 'reiniciar', 'estado'])
        and ('nginx' in lowered or 'httpd' in lowered)
    ):
        request_type = 'manage_service'
        params['service_name'] = 'nginx' if 'nginx' in lowered else 'httpd'
        if 'stop' in lowered or 'detener' in lowered:
            params['state'] = 'stop'
        elif 'restart' in lowered or 'reiniciar' in lowered:
            params['state'] = 'restart'
        elif 'status' in lowered or 'estado' in lowered:
            params['state'] = 'status'
        else:
            params['state'] = 'start'

    elif ('instalar' in lowered or 'install' in lowered) and ('paquete' in lowered or 'package' in lowered):
        request_type = 'install_package'
        package_name = _extract_package_name(lowered)
        if package_name:
            params['package_name'] = package_name
        else:
            params['package_name'] = 'jq'
            warnings.append('No se detectó paquete permitido, se aplicó jq por default.')

    elif (
        ('instalar' in lowered or 'install' in lowered)
        and _extract_package_name(lowered)
        and not ('agente' in lowered or 'agent' in lowered)
    ):
        request_type = 'install_package'
        params['package_name'] = _extract_package_name(lowered)

    elif ('instalar' in lowered or 'install' in lowered) and ('agente' in lowered or 'agent' in lowered):
        request_type = 'install_agent'
        if 'cockpit' in lowered:
            params['agent_name'] = 'cockpit'
        elif 'node_exporter' in lowered:
            params['agent_name'] = 'node_exporter'
        elif 'telegraf' in lowered:
            params['agent_name'] = 'telegraf'
        else:
            params['agent_name'] = 'cockpit'
            warnings.append('No se detectó agente explícito, se aplicó cockpit por default para OL9.')

    elif any(keyword in lowered for keyword in ['template', 'plantilla', 'deploy', 'desplegar']):
        request_type = 'deploy_template'
        params['template_name'] = 'service.conf.j2'
        params['destination_path'] = '/etc/nginx/conf.d/service.conf'
        warnings.append('Se aplicó plantilla/ruta segura por default.')

    elif any(keyword in lowered for keyword in ['crear', 'create']) and any(
        keyword in lowered for keyword in ['carpeta', 'folder', 'directorio', 'directory']
    ):
        request_type = 'create_directory'
        path = _extract_unix_path(text)
        if path:
            params['directory_path'] = path
        else:
            params['directory_path'] = '/opt/automation_factory_lite/work'
            warnings.append('No se detectó ruta, se aplicó /opt/automation_factory_lite/work por default.')

    elif any(keyword in lowered for keyword in ['uptime', 'tiempo encendido']):
        request_type = 'check_uptime'

    elif any(keyword in lowered for keyword in ['estado de parches', 'patch status', 'check-update', 'parches']):
        request_type = 'check_patch_status'

    elif any(keyword in lowered for keyword in ['conectividad', 'connectivity', 'ping']):
        request_type = 'check_connectivity'
        target = _extract_connectivity_target(text, known_hosts)
        if target:
            params['connectivity_target'] = target
        else:
            params['connectivity_target'] = '8.8.8.8'
            warnings.append('No se detectó destino de conectividad, se aplicó 8.8.8.8 por default.')

    targets = _detect_targets(text, known_hosts)
    if request_type in {'check_connectivity'} and not targets:
        targets = [host['hostname'] for host in known_hosts][:1]
    elif not targets and known_hosts:
        targets = [known_hosts[0]['hostname']]
        warnings.append(f"No se detectó target, se aplicó default {targets[0]}.")

    spec = {
        'raw_text': text,
        'request_type': request_type,
        'params': params,
        'targets': targets,
    }

    if request_type == 'unsupported':
        warnings.append('Solicitud fuera del catálogo permitido.')

    return AnalysisResult(spec=spec, warnings=warnings)
