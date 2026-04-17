SAFE_BLUEPRINTS = {
    'create_user': {
        'required': ['username'],
        'optional': ['shell', 'comment'],
        'template': """---
- name: Create restricted Linux user
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Ensure user exists without sudo
      ansible.builtin.user:
        name: "{{ username }}"
        shell: "{{ user_shell | default('/bin/bash') }}"
        comment: "{{ user_comment | default('Managed by Automation Factory Lite') }}"
        groups: ""
        append: false
        state: present
""",
    },
    'install_service': {
        'required': ['service_name'],
        'optional': [],
        'allowed_services': ['nginx', 'httpd'],
        'template': """---
- name: Install approved service
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: true
  tasks:
    - name: Validate service
      ansible.builtin.assert:
        that:
          - service_name in ['nginx', 'httpd']
        fail_msg: "Service not allowed by policy"

    - name: Install approved package
      ansible.builtin.package:
        name: "{{ service_name }}"
        state: present
""",
    },
    'manage_service': {
        'required': ['service_name', 'state'],
        'optional': [],
        'allowed_services': ['nginx', 'httpd'],
        'allowed_states': ['start', 'stop', 'restart', 'status'],
        'template': """---
- name: Manage approved service state
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Validate service
      ansible.builtin.assert:
        that:
          - service_name in ['nginx', 'httpd']
        fail_msg: "Service not allowed by policy"

    - name: Manage service state
      ansible.builtin.service:
        name: "{{ service_name }}"
        state: "{{ desired_state }}"
      when: state != 'status'

    - name: Gather services status
      ansible.builtin.service_facts:
      when: state == 'status'

    - name: Show service status
      ansible.builtin.debug:
        msg: "Service {{ service_name }} state={{ ansible_facts.services[service_name + '.service'].state | default('unknown') }}"
      when: state == 'status'
""",
    },
    'install_agent': {
        'required': ['agent_name'],
        'optional': ['version'],
        'allowed_agents': ['cockpit', 'node_exporter', 'telegraf'],
        'template': """---
- name: Install approved monitoring agent
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: true
  vars:
    agent_packages:
      cockpit:
        primary: "cockpit"
        fallback: "cockpit-ws"
      node_exporter:
        primary: "prometheus-node-exporter"
        fallback: "node_exporter"
      telegraf:
        primary: "telegraf"
        fallback: ""
  tasks:
    - name: Validate agent
      ansible.builtin.assert:
        that:
          - agent_name in ['cockpit', 'node_exporter', 'telegraf']
        fail_msg: "Agent not allowed by policy"

    - name: Resolve package candidates
      ansible.builtin.set_fact:
        agent_package_primary: "{{ agent_packages[agent_name].primary }}"
        agent_package_fallback: "{{ agent_packages[agent_name].fallback }}"

    - name: Install approved agent package
      block:
        - name: Install primary package candidate
          ansible.builtin.package:
            name: "{{ agent_package_primary }}"
            state: present
      rescue:
        - name: Fail when no fallback package is configured
          ansible.builtin.fail:
            msg: "Primary package {{ agent_package_primary }} not available and no fallback is configured."
          when: agent_package_fallback | length == 0

        - name: Install fallback package candidate
          ansible.builtin.package:
            name: "{{ agent_package_fallback }}"
            state: present
          when: agent_package_fallback | length > 0
""",
    },
    'deploy_template': {
        'required': ['template_name', 'destination_path'],
        'optional': ['owner', 'group', 'mode'],
        'allowed_paths': ['/etc/nginx/conf.d', '/etc/httpd/conf.d', '/opt/agents/config'],
        'template': """---
- name: Deploy approved template into allowed path
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Validate destination path
      ansible.builtin.assert:
        that:
          - destination_path.startswith('/etc/nginx/conf.d') or destination_path.startswith('/etc/httpd/conf.d') or destination_path.startswith('/opt/agents/config')
        fail_msg: "Destination path is not allowed by policy"

    - name: Deploy templated file
      ansible.builtin.template:
        src: "{{ template_name }}"
        dest: "{{ destination_path }}"
        owner: "{{ file_owner | default('root') }}"
        group: "{{ file_group | default('root') }}"
        mode: "{{ file_mode | default('0644') }}"
""",
    },
}
