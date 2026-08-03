import json
import os
import tempfile
from pathlib import Path

from qibao_api.speech.models import DEFAULT_SPEECH_SETTINGS, SpeechSettings


class SpeechSettingsRepository:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "speech-settings.json"

    def load(self) -> SpeechSettings:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or set(raw) != {"voice", "rate"}:
                raise ValueError("invalid speech settings")
            return SpeechSettings(voice=raw["voice"], rate=raw["rate"])
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
            return DEFAULT_SPEECH_SETTINGS

    def save(self, settings: SpeechSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(settings.model_dump(), file, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary_path.unlink(missing_ok=True)
            raise
