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
    embedding_dim: int = 1024

    # Non-functional controls
    query_timeout_s: int = 25
    max_top_k: int = 8
    max_context_chars: int = 12000
    enable_rate_limit: bool = True
    rate_limit_requests_per_minute: int = 60

    ingest_data_root: str = "./data"
    ingest_max_retries: int = 2

    enable_tracing: bool = True
    otel_exporter_otlp_endpoint: str = "http://jaeger:4318/v1/traces"

    log_level: str = "INFO"
    enable_metrics: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="EKA_")


settings = Settings()
