from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class LocalSourceSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    auto_discovery: bool = True
    tdx_install_paths: tuple[Path, ...] = ()
    tdx_archive_paths: tuple[Path, ...] = ()
    ths_install_paths: tuple[Path, ...] = ()
    tdx_rpc_enabled: bool = False
    tdx_rpc_url: str | None = None

    @field_validator("tdx_install_paths", "tdx_archive_paths", "ths_install_paths", mode="before")
    @classmethod
    def validate_local_paths(cls, value) -> tuple[Path, ...]:
        if value is None:
            return ()
        paths = []
        seen = set()
        for item in value:
            path = Path(str(item).strip()).expanduser()
            text = str(path)
            if not path.is_absolute() or text.startswith(("\\\\", "//")):
                raise ValueError("source directory must be a local absolute path")
            normalized = path.resolve(strict=False)
            key = str(normalized).casefold()
            if key not in seen:
                seen.add(key)
                paths.append(normalized)
        return tuple(paths)

    @field_validator("tdx_rpc_url")
    @classmethod
    def validate_rpc_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("TDX RPC URL must use an HTTP loopback address")
        return normalized if normalized.endswith("/") else f"{normalized}/"

    @model_validator(mode="after")
    def require_url_for_enabled_rpc(self) -> "LocalSourceSettings":
        if self.tdx_rpc_enabled and self.tdx_rpc_url is None:
            raise ValueError("TDX RPC URL is required when the bridge is enabled")
        return self
