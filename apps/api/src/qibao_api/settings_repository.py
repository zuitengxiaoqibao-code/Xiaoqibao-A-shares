import json
import os
import re
import secrets
import tempfile
import threading
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit

from qibao_api.credential_protection import (
    CredentialProtector,
    default_credential_protector,
)


_MALFORMED_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_MAX_URL_DECODE_PASSES = 8


def _decoded_url_forms(value: str) -> tuple[str, ...]:
    forms = [value]
    current = value
    for _ in range(_MAX_URL_DECODE_PASSES):
        if _MALFORMED_PERCENT_ESCAPE.search(current):
            raise ValueError("base_url contains an invalid percent escape")
        decoded = unquote(current, errors="strict")
        if _MALFORMED_PERCENT_ESCAPE.search(decoded):
            raise ValueError("base_url contains an invalid percent escape")
        forms.append(decoded)
        if decoded == current:
            return tuple(forms)
        current = decoded
    if unquote(current, errors="strict") != current:
        raise ValueError("base_url contains excessive nested encoding")
    return tuple(forms)


@dataclass(frozen=True)
class AISettings:
    base_url: str
    model: str
    api_key: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", self.base_url.strip())
        object.__setattr__(self, "model", unicodedata.normalize("NFKC", self.model).strip())
        object.__setattr__(self, "api_key", unicodedata.normalize("NFKC", self.api_key).strip())
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("base_url must not contain user information")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url must not contain a query or fragment")
        if not self.model:
            raise ValueError("model must not be blank")
        if not self.api_key:
            raise ValueError("api_key must not be blank")
        decoded_urls = _decoded_url_forms(self.base_url)
        if self.api_key in self.model or any(
            self.api_key in unicodedata.normalize("NFKC", value)
            for value in decoded_urls
        ):
            raise ValueError("api_key must not appear in other settings")

    def model_dump(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class UnconfiguredAISettings:
    reason: Literal["missing", "invalid_local_config"]


AISettingsState = AISettings | UnconfiguredAISettings


class AISettingsRepository:
    def __init__(
        self,
        data_dir: Path,
        *,
        protector: CredentialProtector | None = default_credential_protector(),
    ) -> None:
        self.path = data_dir / "ai-settings.json"
        self.protector = protector
        self._lock = threading.RLock()
        self._cached: AISettingsState | None = None

    def load(self) -> AISettingsState:
        with self._lock:
            if self._cached is not None:
                return self._cached
            loaded = self._load_from_disk()
            self._cached = loaded
            return loaded

    def _load_from_disk(self) -> AISettingsState:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("configuration must be an object")
            protected_key = raw.get("api_key_protected")
            is_legacy_plaintext = protected_key is None
            if protected_key is not None:
                if not isinstance(protected_key, str) or self.protector is None:
                    raise ValueError("protected credential is unavailable")
                api_key = self.protector.unprotect(protected_key)
            else:
                api_key = raw["api_key"]
            settings = AISettings(
                base_url=raw["base_url"],
                model=raw["model"],
                api_key=api_key,
            )
            if is_legacy_plaintext and self.protector is not None:
                self.save(settings)
            return settings
        except FileNotFoundError:
            return UnconfiguredAISettings(reason="missing")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
            return UnconfiguredAISettings(reason="invalid_local_config")

    def revision(self) -> str | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, json.JSONDecodeError, OSError):
            return None
        if not isinstance(raw, dict):
            return None
        revision = raw.get("revision")
        if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{32}", revision) is None:
            return None
        return revision

    def save(self, settings: AISettings) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "base_url": settings.base_url,
                "model": settings.model,
                "revision": secrets.token_hex(16),
            }
            if self.protector is None:
                payload["api_key"] = settings.api_key
            else:
                payload["api_key_protected"] = self.protector.protect(settings.api_key)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temporary_path = Path(temporary_name)
            try:
                if os.name != "nt":
                    os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                    json.dump(payload, file, ensure_ascii=False)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary_path, self.path)
                if os.name != "nt":
                    self.path.chmod(0o600)
                self._cached = settings
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                temporary_path.unlink(missing_ok=True)
                raise

    def delete(self) -> None:
        with self._lock:
            self.path.unlink(missing_ok=True)
            self._cached = UnconfiguredAISettings(reason="missing")


class EffectiveAISettingsResolver:
    def __init__(
        self, repository: AISettingsRepository, *, fallback: AISettings | None = None
    ) -> None:
        self.repository = repository
        self._fallback = fallback

    def resolve(self) -> AISettingsState:
        local = self.repository.load()
        if isinstance(local, AISettings):
            return local
        if local.reason == "missing" and self._fallback is not None:
            return self._fallback
        return local
