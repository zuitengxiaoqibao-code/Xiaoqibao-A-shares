from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeLayout:
    root: Path
    web_dir: Path
    config_dir: Path
    data_dir: Path
    legacy_data_dir: Path
    news_dir: Path
    cache_dir: Path
    logs_dir: Path
    models_dir: Path
    exports_dir: Path
    backups_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> "RuntimeLayout":
        resolved = root.expanduser().resolve()
        data_dir = resolved / "data"
        return cls(
            root=resolved,
            web_dir=resolved / "web",
            config_dir=resolved / "config",
            data_dir=data_dir,
            legacy_data_dir=data_dir / "legacy",
            news_dir=resolved / "news",
            cache_dir=resolved / "cache",
            logs_dir=resolved / "logs",
            models_dir=resolved / "models",
            exports_dir=resolved / "exports",
            backups_dir=resolved / "backups",
        )

    def directory_map(self) -> dict[str, Path]:
        return {
            "web": self.web_dir,
            "config": self.config_dir,
            "data": self.data_dir,
            "legacy_data": self.legacy_data_dir,
            "news": self.news_dir,
            "cache": self.cache_dir,
            "logs": self.logs_dir,
            "models": self.models_dir,
            "exports": self.exports_dir,
            "backups": self.backups_dir,
        }

    def ensure(self) -> None:
        for name, path in self.directory_map().items():
            if name != "web":
                path.mkdir(parents=True, exist_ok=True)
