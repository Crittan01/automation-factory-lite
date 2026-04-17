from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = Field(default='dev', alias='APP_ENV')
    app_log_level: str = Field(default='INFO', alias='APP_LOG_LEVEL')

    backend_host: str = Field(default='0.0.0.0', alias='BACKEND_HOST')
    backend_port: int = Field(default=8000, alias='BACKEND_PORT')

    database_url: str = Field(default='sqlite:///./automation_factory_lite.db', alias='DATABASE_URL')

    mock_mode: bool = Field(default=True, alias='MOCK_MODE')

    openai_api_key: str | None = Field(default=None, alias='OPENAI_API_KEY')
    openai_model: str = Field(default='gpt-4.1-mini', alias='OPENAI_MODEL')
    enable_langgraph: bool = Field(default=False, alias='ENABLE_LANGGRAPH')

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
