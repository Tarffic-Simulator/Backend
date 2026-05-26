from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Backend API"
    app_version: str = "0.1.0"

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str
    engine_api_url: str
    create_tables_on_startup: bool = False
    data_encryption_key: str | None = None
    log_level: str = "INFO"
    log_file: str = "logs/app.txt"

    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
