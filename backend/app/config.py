from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    claude_bin: str = "claude"
    db_path: Path = DATA_DIR / "foreman.db"
    reports_dir: Path = DATA_DIR / "reports"
    tmp_dir: Path = DATA_DIR / "tmp"
    host: str = "127.0.0.1"
    port: int = 8000
    default_timeout_seconds: int = 1800
    default_tool_budget: int = 80

    model_config = {"env_prefix": "FOREMAN_", "env_file": ".env"}


settings = Settings()
settings.reports_dir.mkdir(parents=True, exist_ok=True)
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
