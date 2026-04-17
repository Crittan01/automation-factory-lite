from types import SimpleNamespace

from services.awx_client.client import MockAWXClient, build_awx_client


def test_mock_awx_launch() -> None:
    client = MockAWXClient()
    client.publish_job_template('demo-template', 'generated/demo/playbook.yml', 'MockInventory')
    launch = client.launch_job('demo-template', ['ol9server1'], {'x': 1})

    assert launch.mode == 'mock'
    assert launch.status == 'successful'


def test_awx_fallback_to_mock_when_real_missing_config() -> None:
    settings = SimpleNamespace(
        awx_mode='real',
        awx_url=None,
        awx_token=None,
        awx_organization='org',
        awx_project='project',
        awx_inventory='inventory',
        awx_verify_tls=False,
        awx_credential_id=None,
    )
    client = build_awx_client(settings)
    assert isinstance(client, MockAWXClient)
