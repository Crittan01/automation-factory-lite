from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
import time

import requests


@dataclass
class AWXBootstrapResult:
    mode: str
    organization: str
    project: str
    inventory: str
    notes: str
    resources: dict


@dataclass
class AWXExecutionResult:
    mode: str
    template_name: str
    job_id: str
    status: str
    summary: str


JOB_TEMPLATE_DEFINITIONS = [
    ('AFL - Create User', 'ansible/playbooks/create_user.yml'),
    ('AFL - Delete User', 'ansible/playbooks/delete_user.yml'),
    ('AFL - Reset Password', 'ansible/playbooks/reset_password.yml'),
    ('AFL - Add SSH Key', 'ansible/playbooks/add_ssh_key.yml'),
    ('AFL - Create Directory', 'ansible/playbooks/create_directory.yml'),
    ('AFL - Install Service', 'ansible/playbooks/install_service.yml'),
    ('AFL - Install Package', 'ansible/playbooks/install_package.yml'),
    ('AFL - Restart Service', 'ansible/playbooks/restart_service.yml'),
    ('AFL - Manage Service', 'ansible/playbooks/manage_service.yml'),
    ('AFL - Install Agent', 'ansible/playbooks/install_agent.yml'),
    ('AFL - Deploy Template', 'ansible/playbooks/deploy_template.yml'),
    ('AFL - Check Uptime', 'ansible/playbooks/check_uptime.yml'),
    ('AFL - Check Patch Status', 'ansible/playbooks/check_patch_status.yml'),
    ('AFL - Check Connectivity', 'ansible/playbooks/check_connectivity.yml'),
]

WORKFLOW_TEMPLATE_NAME = 'AFL - Low Risk Factory Workflow'


class BaseAWXClient:
    mode: str = 'base'

    def bootstrap(self) -> AWXBootstrapResult:
        raise NotImplementedError

    def publish_job_template(self, name: str, playbook_path: str, inventory_name: str) -> dict:
        raise NotImplementedError

    def launch_job(self, template_name: str, limit_hosts: list[str], extra_vars: dict) -> AWXExecutionResult:
        raise NotImplementedError


class MockAWXClient(BaseAWXClient):
    mode = 'mock'

    def __init__(self) -> None:
        self.templates: dict[str, dict] = {}

    def bootstrap(self) -> AWXBootstrapResult:
        return AWXBootstrapResult(
            mode=self.mode,
            organization='MockOrg',
            project='MockProject',
            inventory='MockInventory',
            notes='AWX mock bootstrap completed.',
            resources={
                'job_templates': [],
                'workflow_templates': [],
                'hosts': [],
            },
        )

    def publish_job_template(self, name: str, playbook_path: str, inventory_name: str) -> dict:
        template_id = str(uuid.uuid4())
        self.templates[name] = {
            'id': template_id,
            'name': name,
            'playbook_path': playbook_path,
            'inventory_name': inventory_name,
        }
        return {'id': template_id, 'name': name}

    def launch_job(self, template_name: str, limit_hosts: list[str], extra_vars: dict) -> AWXExecutionResult:
        if template_name not in self.templates:
            self.publish_job_template(template_name, 'unknown', 'MockInventory')

        job_id = f'mock-job-{uuid.uuid4()}'
        summary = (
            f"Executed template '{template_name}' on hosts {', '.join(limit_hosts)} "
            f"with vars keys={sorted(extra_vars.keys())}"
        )
        return AWXExecutionResult(
            mode=self.mode,
            template_name=template_name,
            job_id=job_id,
            status='successful',
            summary=summary,
        )


class RealAWXClient(BaseAWXClient):
    mode = 'real'

    def __init__(
        self,
        base_url: str,
        token: str,
        organization: str,
        project: str,
        inventory: str,
        verify_tls: bool,
        credential_id: str | None,
        project_scm_type: str,
        project_scm_url: str | None,
        project_scm_branch: str,
        project_scm_update_on_launch: bool,
        machine_credential_name: str | None,
        hosts: list[dict],
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.organization = organization
        self.project = project
        self.inventory = inventory
        self.verify_tls = verify_tls
        self.credential_id = credential_id
        self.project_scm_type = project_scm_type
        self.project_scm_url = project_scm_url
        self.project_scm_branch = project_scm_branch
        self.project_scm_update_on_launch = project_scm_update_on_launch
        self.machine_credential_name = machine_credential_name
        self.hosts = hosts

        self.session = requests.Session()
        self.session.headers.update(
            {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        merged_params = {'page_size': 200}
        if params:
            merged_params.update(params)
        res = self.session.get(f'{self.base_url}{path}', params=merged_params, timeout=30, verify=self.verify_tls)
        res.raise_for_status()
        return res.json()

    def _post(self, path: str, data: dict) -> dict:
        res = self.session.post(f'{self.base_url}{path}', json=data, timeout=30, verify=self.verify_tls)
        res.raise_for_status()
        if not res.text.strip():
            return {}
        return res.json()

    def _patch(self, path: str, data: dict) -> dict:
        res = self.session.patch(f'{self.base_url}{path}', json=data, timeout=30, verify=self.verify_tls)
        res.raise_for_status()
        return res.json()

    def _find_named(self, endpoint: str, name: str, extra_filters: dict | None = None) -> dict | None:
        params: dict = {'name': name}
        if extra_filters:
            params.update(extra_filters)
        existing = self._get(endpoint, params=params)
        for item in existing.get('results', []):
            if item.get('name') == name:
                return item
        return None

    def _find_or_create_named(self, endpoint: str, name: str, payload: dict, extra_filters: dict | None = None) -> dict:
        item = self._find_named(endpoint, name, extra_filters=extra_filters)
        if item:
            return item
        return self._post(endpoint, payload)

    def _resolve_organization(self) -> dict:
        named = self._find_named('/api/v2/organizations/', self.organization)
        if named:
            return named

        try:
            return self._post('/api/v2/organizations/', {'name': self.organization})
        except requests.HTTPError as exc:
            response = exc.response
            if response is not None and response.status_code == 403:
                visible = self._get('/api/v2/organizations/', params={'page_size': 50})
                for org in visible.get('results', []):
                    can_edit = (((org.get('summary_fields') or {}).get('user_capabilities') or {}).get('edit') is True)
                    if can_edit:
                        return org
            raise

    def _create_or_update_project(self, org_id: int) -> dict:
        payload = {
            'name': self.project,
            'organization': org_id,
            'scm_type': self.project_scm_type,
            'scm_branch': self.project_scm_branch,
            'scm_update_on_launch': self.project_scm_update_on_launch,
        }

        payload['scm_url'] = self.project_scm_url or ''

        existing = self._find_named('/api/v2/projects/', self.project)
        if existing:
            return self._patch(f"/api/v2/projects/{existing['id']}/", payload)

        try:
            return self._post('/api/v2/projects/', payload)
        except requests.HTTPError:
            projects = self._get('/api/v2/projects/', params={'page_size': 50, 'order_by': '-modified'})
            for project in projects.get('results', []):
                can_edit = (((project.get('summary_fields') or {}).get('user_capabilities') or {}).get('edit') is True)
                if can_edit:
                    return project
            raise

    def _ensure_host(self, inventory_id: int, name: str, ip: str) -> dict:
        variables = json.dumps({'ansible_host': ip}, indent=2)
        payload = {
            'name': name,
            'inventory': inventory_id,
            'enabled': True,
            'variables': variables,
        }
        existing = self._find_named('/api/v2/hosts/', name, extra_filters={'inventory': inventory_id})
        if existing:
            return self._patch(f"/api/v2/hosts/{existing['id']}/", payload)
        return self._post('/api/v2/hosts/', payload)

    def _resolve_credential_id(self) -> int | None:
        if self.credential_id:
            try:
                return int(self.credential_id)
            except ValueError:
                pass

        if self.machine_credential_name:
            named = self._find_named('/api/v2/credentials/', self.machine_credential_name)
            if named:
                return int(named['id'])

        credential_page = self._get('/api/v2/credentials/', params={'order_by': '-modified'})
        for cred in credential_page.get('results', []):
            kind = str(cred.get('kind') or '').lower()
            if kind in {'ssh', 'net'}:
                return int(cred['id'])

        return None

    def _associate_credential_to_job_template(self, template_id: int, credential_id: int) -> None:
        current = self._get(f'/api/v2/job_templates/{template_id}/credentials/')
        for credential in current.get('results', []):
            if int(credential.get('id', 0)) == credential_id:
                return
        self._post(f'/api/v2/job_templates/{template_id}/credentials/', {'id': credential_id})

    def _ensure_job_template(self, *, name: str, playbook_path: str, project_id: int, inventory_id: int) -> dict:
        payload = {
            'name': name,
            'job_type': 'run',
            'inventory': inventory_id,
            'project': project_id,
            'playbook': playbook_path,
            'ask_variables_on_launch': True,
            'ask_limit_on_launch': True,
            'ask_tags_on_launch': True,
        }
        existing = self._find_named('/api/v2/job_templates/', name)
        if existing:
            return self._patch(f"/api/v2/job_templates/{existing['id']}/", payload)
        return self._post('/api/v2/job_templates/', payload)

    def _ensure_workflow(self, org_id: int, inventory_id: int, starter_job_template_id: int) -> dict:
        payload = {
            'name': WORKFLOW_TEMPLATE_NAME,
            'organization': org_id,
            'inventory': inventory_id,
            'ask_variables_on_launch': True,
        }
        existing = self._find_named('/api/v2/workflow_job_templates/', WORKFLOW_TEMPLATE_NAME)
        if existing:
            workflow = self._patch(f"/api/v2/workflow_job_templates/{existing['id']}/", payload)
        else:
            workflow = self._post('/api/v2/workflow_job_templates/', payload)

        node_payload = {
            'workflow_job_template': workflow['id'],
            'unified_job_template': starter_job_template_id,
            'all_parents_must_converge': False,
        }
        nodes = self._get('/api/v2/workflow_job_template_nodes/', params={'workflow_job_template': workflow['id']})
        for node in nodes.get('results', []):
            if int(node.get('unified_job_template', 0)) == starter_job_template_id:
                return workflow

        self._post('/api/v2/workflow_job_template_nodes/', node_payload)
        return workflow

    def _list_project_playbooks(self, project_id: int) -> list[str]:
        response = self._get(f'/api/v2/projects/{project_id}/playbooks/')
        if isinstance(response, list):
            return [str(item) for item in response]
        return []

    def _sync_project(self, project_id: int, timeout_seconds: int = 180) -> None:
        update = self._post(f'/api/v2/projects/{project_id}/update/', {})
        update_id = int(update.get('project_update') or update.get('id') or 0)
        if update_id <= 0:
            return

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            status = self._get(f'/api/v2/project_updates/{update_id}/')
            state = str(status.get('status') or '').lower()
            if state in {'successful', 'failed', 'error', 'canceled'}:
                if state != 'successful':
                    raise RuntimeError(
                        f'AWX project sync failed for project_id={project_id} with status={state}.'
                    )
                return
            time.sleep(2)

        raise RuntimeError(f'AWX project sync timeout for project_id={project_id}.')

    def bootstrap(self) -> AWXBootstrapResult:
        org = self._resolve_organization()
        project = self._create_or_update_project(org_id=org['id'])
        inv = self._find_or_create_named(
            '/api/v2/inventories/',
            self.inventory,
            {'name': self.inventory, 'organization': org['id']},
        )

        created_hosts: list[str] = []
        for host in self.hosts:
            created = self._ensure_host(inv['id'], host['name'], host['ip'])
            created_hosts.append(created['name'])

        credential_id = self._resolve_credential_id()

        created_templates: list[str] = []
        first_template_id: int | None = None
        playbook_mapping: dict[str, str] = {}
        unresolved_playbooks: dict[str, str] = {}
        available_playbooks = self._list_project_playbooks(project['id'])
        if not available_playbooks and self.project_scm_type != 'manual':
            self._sync_project(int(project['id']))
            available_playbooks = self._list_project_playbooks(project['id'])
        fallback_playbook = available_playbooks[0] if available_playbooks else None

        for name, playbook_path in JOB_TEMPLATE_DEFINITIONS:
            selected_playbook = playbook_path
            if playbook_path not in available_playbooks:
                if fallback_playbook is None:
                    raise RuntimeError(
                        f"Project {project.get('name')} does not expose playbooks through AWX API. "
                        'Configure SCM and sync project first.'
                    )
                selected_playbook = fallback_playbook
                unresolved_playbooks[name] = playbook_path

            template = self._ensure_job_template(
                name=name,
                playbook_path=selected_playbook,
                project_id=project['id'],
                inventory_id=inv['id'],
            )
            created_templates.append(template['name'])
            playbook_mapping[name] = selected_playbook
            if first_template_id is None:
                first_template_id = int(template['id'])

            if credential_id is not None:
                self._associate_credential_to_job_template(int(template['id']), credential_id)

        workflow = None
        if first_template_id is not None:
            workflow = self._ensure_workflow(org['id'], inv['id'], first_template_id)

        notes = 'AWX scenario bootstrap completed.'
        if org.get('name') != self.organization:
            notes += f" Requested org '{self.organization}' was not available; used '{org.get('name')}'."
        if project.get('name') != self.project:
            notes += f" Requested project '{self.project}' was not available; used '{project.get('name')}'."
        if self.project_scm_type != 'manual' and not self.project_scm_url:
            notes += ' Warning: SCM type is not manual but AWX_PROJECT_SCM_URL is empty.'
        if credential_id is None:
            notes += ' No machine credential was auto-associated; provide AWX_CREDENTIAL_ID for real execution.'
        if unresolved_playbooks:
            notes += ' Some templates use fallback playbooks because requested paths were missing in project.'

        return AWXBootstrapResult(
            mode=self.mode,
            organization=org['name'],
            project=project['name'],
            inventory=inv['name'],
            notes=notes,
            resources={
                'project_id': project['id'],
                'inventory_id': inv['id'],
                'credential_id': credential_id,
                'hosts': created_hosts,
                'job_templates': created_templates,
                'workflow_template': workflow['name'] if workflow else None,
                'project_scm_type': self.project_scm_type,
                'project_scm_url': self.project_scm_url,
                'available_playbooks': available_playbooks,
                'playbook_mapping': playbook_mapping,
                'unresolved_playbooks': unresolved_playbooks,
            },
        )

    def _resolve_project_inventory_ids(self) -> tuple[int, int]:
        projects = self._get('/api/v2/projects/', params={'name': self.project}).get('results', [])
        inventories = self._get('/api/v2/inventories/', params={'name': self.inventory}).get('results', [])
        if not projects or not inventories:
            raise RuntimeError('Project or inventory not found in AWX. Run bootstrap first.')
        return int(projects[0]['id']), int(inventories[0]['id'])

    def publish_job_template(self, name: str, playbook_path: str, inventory_name: str) -> dict:
        project_id, inventory_id = self._resolve_project_inventory_ids()
        template = self._ensure_job_template(
            name=name,
            playbook_path=playbook_path,
            project_id=project_id,
            inventory_id=inventory_id,
        )

        credential_id = self._resolve_credential_id()
        if credential_id is not None:
            self._associate_credential_to_job_template(int(template['id']), credential_id)

        return template

    def launch_job(self, template_name: str, limit_hosts: list[str], extra_vars: dict) -> AWXExecutionResult:
        templates = self._get('/api/v2/job_templates/', params={'name': template_name}).get('results', [])
        if not templates:
            raise RuntimeError(f'Job template {template_name} does not exist in AWX.')
        template = templates[0]
        host_pattern = ':'.join(limit_hosts)
        launch_vars = dict(extra_vars)
        if host_pattern:
            # Compatibility helpers:
            # - V1 playbooks consume `target_hosts`.
            # - fallback lab playbooks in shared repos may consume `target`.
            launch_vars.setdefault('target_hosts', host_pattern)
            launch_vars.setdefault('target', host_pattern)

        launch_data = {
            'extra_vars': launch_vars,
            'limit': host_pattern,
        }
        launch_res = self._post(f"/api/v2/job_templates/{template['id']}/launch/", launch_data)

        return AWXExecutionResult(
            mode=self.mode,
            template_name=template_name,
            job_id=str(launch_res.get('job') or launch_res.get('id')),
            status='launched',
            summary=f"AWX job launched at {datetime.utcnow().isoformat()} for hosts={limit_hosts}",
        )


def build_awx_client(settings) -> BaseAWXClient:
    if settings.awx_mode != 'real':
        return MockAWXClient()

    if not settings.awx_url or not settings.awx_token:
        return MockAWXClient()

    try:
        return RealAWXClient(
            base_url=settings.awx_url,
            token=settings.awx_token,
            organization=settings.awx_organization,
            project=settings.awx_project,
            inventory=settings.awx_inventory,
            verify_tls=settings.awx_verify_tls,
            credential_id=settings.awx_credential_id,
            project_scm_type=settings.awx_project_scm_type,
            project_scm_url=settings.awx_project_scm_url,
            project_scm_branch=settings.awx_project_scm_branch,
            project_scm_update_on_launch=settings.awx_project_scm_update_on_launch,
            machine_credential_name=settings.awx_machine_credential_name,
            hosts=[
                {'name': settings.target_host_1_name, 'ip': settings.target_host_1},
                {'name': settings.target_host_2_name, 'ip': settings.target_host_2},
            ],
        )
    except Exception:
        return MockAWXClient()
