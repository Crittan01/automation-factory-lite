from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    spec: dict
    warnings: list[str]


def _detect_targets(text: str, known_hosts: list[dict]) -> list[str]:
    lowered = text.lower()
    targets: list[str] = []

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

    elif ('instalar' in lowered or 'install' in lowered) and ('nginx' in lowered or 'httpd' in lowered):
        request_type = 'install_service'
        params['service_name'] = 'nginx' if 'nginx' in lowered else 'httpd'

    elif any(keyword in lowered for keyword in ['start', 'stop', 'restart', 'status', 'iniciar', 'detener', 'reiniciar', 'estado']):
        if 'nginx' in lowered or 'httpd' in lowered:
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

    targets = _detect_targets(text, known_hosts)
    if not targets and known_hosts:
        targets = [known_hosts[0]['hostname']]
        warnings.append(f"No se detectó target, se aplicó default {targets[0]}.")

    spec = {
        'raw_text': text,
        'request_type': request_type,
        'params': params,
        'targets': targets,
    }

    if request_type == 'unsupported':
        warnings.append('Solicitud fuera del catálogo permitido V1.')

    return AnalysisResult(spec=spec, warnings=warnings)
