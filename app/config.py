from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FACE_APP_", env_file=".env", extra="ignore")

    app_name: str = "Face Recognition App"
    secret_key: str = "change-me-in-production"
    token_expire_minutes: int = 60 * 8
    algorithm: str = "HS256"
    database_url: str = "sqlite:///./face_app.db"

    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    session_cookie_name: str = "session_token"
    csrf_cookie_name: str = "csrf_token"

    embeddings_model_version: str = "insightface-v1"
    strict_match_threshold: float = 0.82
    webhook_max_retries: int = 5
    webhook_retry_base_seconds: int = 10

    snapshot_dir: str = "data/snapshots"
    sample_dir: str = "data/samples"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
