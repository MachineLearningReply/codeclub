from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env.local")

    db_connection_string: str
    blob_storage_connection_string: str | None = None
    blob_storage_account_url: str | None = None
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str


app_settings = AppSettings()
