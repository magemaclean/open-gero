from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OpenGero"
    app_version: str = "0.1.0"
    secret_key: str = "change-me-in-production-opengero"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24 * 7

    database_url: str = "sqlite:///./opengero.db"
    redis_url: str = "redis://localhost:6379/0"

    storage_dir: Path = Path("./data/runtime")
    datasets_dir: Path = ROOT / "data" / "datasets"
    targets_dir: Path = ROOT / "data" / "targets"

    cors_origins: str = "http://localhost:5173,http://localhost:8080,http://localhost:3000"

    max_import_rows: int = 50_000
    descriptor_inline_limit: int = 500
    default_batch_size: int = 100
    max_docking_library: int = 10_000
    soft_delete_days: int = 30

    vina_binary: str = "vina"
    obabel_binary: str = "obabel"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
