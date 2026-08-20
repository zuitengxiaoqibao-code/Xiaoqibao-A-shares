import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from qibao_api.local_sources.discovery import LocalTerminalDiscoveryResult
from qibao_api.local_sources.models import LocalSourceSettings


@dataclass(frozen=True)
class LocalSourceSettingsRecord:
    settings: LocalSourceSettings
    state: Literal["ready", "default", "invalid_local_config"]


class LocalSourceSettingsRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> LocalSourceSettingsRecord:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("settings payload must be an object")
            return LocalSourceSettingsRecord(
                settings=LocalSourceSettings.model_validate(payload),
                state="ready",
            )
        except FileNotFoundError:
            return LocalSourceSettingsRecord(
                settings=LocalSourceSettings(),
                state="default",
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError, ValidationError):
            return LocalSourceSettingsRecord(
                settings=LocalSourceSettings(),
                state="invalid_local_config",
            )

    def save(self, settings: LocalSourceSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    settings.model_dump(mode="json"),
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary_path.unlink(missing_ok=True)
            raise


class LocalTerminalDiscoverySnapshotRepository:
    """Small atomic cache for the last verified local-terminal scan."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(
        self, settings: LocalSourceSettings
    ) -> LocalTerminalDiscoveryResult | None:
        try:
            snapshot = LocalTerminalDiscoveryResult.model_validate(
                json.loads(self.path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError, TypeError, ValidationError):
            return None
        if snapshot.settings != settings:
            return None
        return snapshot

    def save(self, snapshot: LocalTerminalDiscoveryResult) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(snapshot.model_dump_json())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary_path.unlink(missing_ok=True)
            raise
