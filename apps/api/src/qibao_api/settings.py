from pathlib import Path

from pydantic import computed_field
from pydantic import field_validator
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from qibao_api.settings_repository import AISettings


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = PROJECT_ROOT / ".runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QIBAO_", extra="ignore")

    data_dir: Path = DEFAULT_DATA_DIR
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 30
    ai_base_url: str | None = None
    ai_api_key: SecretStr | None = None
    ai_model: str | None = None

    @field_validator("data_dir", mode="after")
    @classmethod
    def resolve_data_dir(cls, value: Path) -> Path:
        return value if value.is_absolute() else (PROJECT_ROOT / value).resolve()

    @computed_field
    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'qibao.db').as_posix()}"

    @computed_field
    @property
    def decision_database_path(self) -> Path:
        return self.data_dir / "decisions.sqlite3"

    @property
    def initial_ai_settings(self) -> AISettings | None:
        if self.ai_base_url is None or self.ai_api_key is None or self.ai_model is None:
            return None
        try:
            return AISettings(
                base_url=self.ai_base_url,
                model=self.ai_model,
                api_key=self.ai_api_key.get_secret_value(),
            )
        except ValueError:
            return None
