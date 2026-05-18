from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    perplexity_api_key: str
    anthropic_api_key: str
    app_password: str
    perplexity_model: str = "sonar-pro"
    claude_model: str = "claude-sonnet-4-6"


def get_settings() -> Settings:
    return Settings()  # raises ValidationError if any required var is absent
