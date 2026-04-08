from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    gc_password: str = "gc-secret-2024"   # Simple GC auth — replace in production
    secret_key: str = "change-me-in-production"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
