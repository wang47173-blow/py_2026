from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "enterprise-knowledge-assistant-gateway"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8080

    database_url: str = "postgresql+psycopg://app:app@postgres:5432/eka"

    # Fireworks + GLM-5 (LangChain)
    fireworks_api_key: str = ""
    fireworks_model: str = "accounts/fireworks/models/glm-5"

    log_level: str = "INFO"
    enable_metrics: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="EKA_")


settings = Settings()
