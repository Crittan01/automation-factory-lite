from __future__ import annotations

from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = Field(default='dev', alias='APP_ENV')
    app_log_level: str = Field(default='INFO', alias='APP_LOG_LEVEL')

    backend_host: str = Field(default='0.0.0.0', alias='BACKEND_HOST')
    backend_port: int = Field(default=18010, alias='BACKEND_PORT')

    database_url: str = Field(default='sqlite:///./automation_factory_lite.db', alias='DATABASE_URL')

    mock_mode: bool = Field(default=True, alias='MOCK_MODE')

    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices('OPENAI_API_KEY', 'OPENAI_KEY'),
        alias='OPENAI_API_KEY',
    )
    openai_model: str = Field(default='gpt-4.1-mini', alias='OPENAI_MODEL')
    enable_langgraph: bool = Field(default=False, alias='ENABLE_LANGGRAPH')

    itsm_webhook_enabled: bool = Field(default=False, alias='ITSM_WEBHOOK_ENABLED')
    itsm_webhook_url: str | None = Field(default=None, alias='ITSM_WEBHOOK_URL')
    itsm_webhook_token: str | None = Field(default=None, alias='ITSM_WEBHOOK_TOKEN')
    itsm_webhook_timeout_seconds: int = Field(default=5, alias='ITSM_WEBHOOK_TIMEOUT_SECONDS')

    servicenow_sim_host: str = Field(default='0.0.0.0', alias='SERVICENOW_SIM_HOST')
    servicenow_sim_port: int = Field(default=18095, alias='SERVICENOW_SIM_PORT')

    servicenow_mcp_enabled: bool = Field(default=True, alias='SERVICENOW_MCP_ENABLED')
    servicenow_mcp_mode: str = Field(default='external_http_bridge', alias='SERVICENOW_MCP_MODE')
    servicenow_mcp_endpoint: str | None = Field(default=None, alias='SERVICENOW_MCP_ENDPOINT')
    servicenow_mcp_server_cmd: str = Field(
        default='python3 services/servicenow_sim/mcp_server.py',
        alias='SERVICENOW_MCP_SERVER_CMD',
    )
    servicenow_external_enabled: bool = Field(default=True, alias='SERVICENOW_EXTERNAL_ENABLED')
    servicenow_external_base_url: str = Field(
        default='http://127.0.0.1:18095',
        alias='SERVICENOW_EXTERNAL_BASE_URL',
    )
    servicenow_external_verify_tls: bool = Field(default=False, alias='SERVICENOW_EXTERNAL_VERIFY_TLS')
    servicenow_external_timeout_seconds: int = Field(default=5, alias='SERVICENOW_EXTERNAL_TIMEOUT_SECONDS')

    awx_mode: str = Field(default='mock', alias='AWX_MODE')
    awx_url: str | None = Field(default=None, alias='AWX_URL')
    awx_token: str | None = Field(default=None, alias='AWX_TOKEN')
    awx_verify_tls: bool = Field(default=False, alias='AWX_VERIFY_TLS')
    awx_organization: str = Field(default='AutomationFactory', alias='AWX_ORGANIZATION')
    awx_project: str = Field(default='AutomationFactoryProject', alias='AWX_PROJECT')
    awx_inventory: str = Field(default='AutomationFactoryInventory', alias='AWX_INVENTORY')
    awx_credential_id: str | None = Field(default=None, alias='AWX_CREDENTIAL_ID')
    awx_project_scm_type: str = Field(default='git', alias='AWX_PROJECT_SCM_TYPE')
    awx_project_scm_url: str | None = Field(default=None, alias='AWX_PROJECT_SCM_URL')
    awx_project_scm_branch: str = Field(default='main', alias='AWX_PROJECT_SCM_BRANCH')
    awx_project_scm_update_on_launch: bool = Field(default=False, alias='AWX_PROJECT_SCM_UPDATE_ON_LAUNCH')
    awx_machine_credential_name: str | None = Field(default=None, alias='AWX_MACHINE_CREDENTIAL_NAME')

    target_host_1: str = Field(default='192.168.250.30', alias='TARGET_HOST_1')
    target_host_1_name: str = Field(default='ol9server1', alias='TARGET_HOST_1_NAME')
    target_host_2: str = Field(default='192.168.250.40', alias='TARGET_HOST_2')
    target_host_2_name: str = Field(default='rocky9server1', alias='TARGET_HOST_2_NAME')


@lru_cache
def get_settings() -> Settings:
    return Settings()
