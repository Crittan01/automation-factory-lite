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
    'delete_user': {
        'required': ['username'],
        'optional': ['remove_home'],
        'template': """---
- name: Delete Linux user safely
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Ensure user is absent
      ansible.builtin.user:
        name: "{{ username }}"
        state: absent
        remove: "{{ remove_home | default(false) }}"
""",
    },
    'reset_password': {
        'required': ['username', 'password_hash'],
        'optional': [],
        'template': """---
- name: Reset password using pre-hashed value
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Ensure password hash is a SHA-512 crypt hash
      ansible.builtin.assert:
        that:
          - password_hash.startswith('$6$')
        fail_msg: "password_hash must start with $6$"

    - name: Update user password hash
      ansible.builtin.user:
        name: "{{ username }}"
        password: "{{ password_hash }}"
        update_password: always
""",
    },
    'add_ssh_key': {
        'required': ['username', 'ssh_public_key'],
        'optional': [],
        'template': """---
- name: Add authorized SSH key
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Validate supported key format
      ansible.builtin.assert:
        that:
          - ssh_public_key.startswith('ssh-rsa ') or ssh_public_key.startswith('ssh-ed25519 ')
        fail_msg: "Only ssh-rsa and ssh-ed25519 keys are allowed"

    - name: Ensure .ssh directory exists
      ansible.builtin.file:
        path: "/home/{{ username }}/.ssh"
        state: directory
        owner: "{{ username }}"
        group: "{{ username }}"
        mode: "0700"

    - name: Ensure authorized key exists for user
      ansible.builtin.lineinfile:
        path: "/home/{{ username }}/.ssh/authorized_keys"
        line: "{{ ssh_public_key }}"
        create: true
        owner: "{{ username }}"
        group: "{{ username }}"
        mode: "0600"
        state: present
""",
    },
    'create_directory': {
        'required': ['directory_path'],
        'optional': ['owner', 'group', 'mode'],
        'allowed_paths': ['/opt/automation_factory_lite', '/srv/automation_factory_lite', '/var/tmp/automation_factory_lite'],
        'template': """---
- name: Create approved directory
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Validate destination path
      ansible.builtin.assert:
        that:
          - >
            directory_path.startswith('/opt/automation_factory_lite')
            or directory_path.startswith('/srv/automation_factory_lite')
            or directory_path.startswith('/var/tmp/automation_factory_lite')
        fail_msg: "Directory path is outside approved scope"

    - name: Ensure directory exists
      ansible.builtin.file:
        path: "{{ directory_path }}"
        state: directory
        owner: "{{ dir_owner | default('root') }}"
        group: "{{ dir_group | default('root') }}"
        mode: "{{ dir_mode | default('0755') }}"
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
    'install_package': {
        'required': ['package_name'],
        'optional': [],
        'allowed_packages': ['jq', 'curl', 'git', 'rsync', 'htop', 'cockpit'],
        'template': """---
- name: Install approved package
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: true
  tasks:
    - name: Validate package
      ansible.builtin.assert:
        that:
          - package_name in ['jq', 'curl', 'git', 'rsync', 'htop', 'cockpit']
        fail_msg: "Package not allowed by policy"

    - name: Ensure package is present
      ansible.builtin.package:
        name: "{{ package_name }}"
        state: present
""",
    },
    'restart_service': {
        'required': ['service_name'],
        'optional': [],
        'allowed_services': ['nginx', 'httpd', 'cockpit'],
        'template': """---
- name: Restart approved service
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Validate service
      ansible.builtin.assert:
        that:
          - service_name in ['nginx', 'httpd', 'cockpit']
        fail_msg: "Service not allowed for restart"

    - name: Restart service
      ansible.builtin.service:
        name: "{{ service_name }}"
        state: restarted
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
    'check_uptime': {
        'required': [],
        'optional': [],
        'template': """---
- name: Gather uptime diagnostics
  hosts: {{ targets_pattern }}
  become: false
  gather_facts: false
  tasks:
    - name: Get uptime
      ansible.builtin.command: uptime -p
      changed_when: false
      register: uptime_result

    - name: Show uptime
      ansible.builtin.debug:
        var: uptime_result.stdout
""",
    },
    'check_patch_status': {
        'required': [],
        'optional': [],
        'template': """---
- name: Gather patch status diagnostics
  hosts: {{ targets_pattern }}
  become: true
  gather_facts: false
  tasks:
    - name: Run package update check
      ansible.builtin.command: dnf -q check-update
      changed_when: false
      failed_when: patch_check.rc not in [0, 100]
      register: patch_check

    - name: Show patch check summary
      ansible.builtin.debug:
        msg: "Patch check rc={{ patch_check.rc }} (0=no updates, 100=updates available)"
""",
    },
    'check_connectivity': {
        'required': ['connectivity_target'],
        'optional': [],
        'template': """---
- name: Run connectivity diagnostics
  hosts: {{ targets_pattern }}
  become: false
  gather_facts: false
  tasks:
    - name: Ping connectivity target
      ansible.builtin.command: ping -c 1 -W 2 {{ connectivity_target }}
      changed_when: false
      failed_when: false
      register: connectivity_probe

    - name: Report connectivity result
      ansible.builtin.debug:
        msg: "Connectivity rc={{ connectivity_probe.rc }} target={{ connectivity_target }}"
""",
    },
}
