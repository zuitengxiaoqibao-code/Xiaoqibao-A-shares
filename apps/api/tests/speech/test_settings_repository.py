import json
from pathlib import Path

import pytest

from qibao_api.speech.models import DEFAULT_SPEECH_SETTINGS, SpeechSettings
from qibao_api.speech.settings_repository import SpeechSettingsRepository


def test_repository_returns_beginner_friendly_default_when_file_is_missing(
    tmp_path: Path,
) -> None:
    repository = SpeechSettingsRepository(tmp_path)

    assert repository.load() == DEFAULT_SPEECH_SETTINGS


def test_repository_round_trips_voice_and_rate_atomically(tmp_path: Path) -> None:
    repository = SpeechSettingsRepository(tmp_path)
    settings = SpeechSettings(voice="zh-CN-YunxiNeural", rate=12)

    repository.save(settings)

    assert repository.load() == settings
    assert json.loads(repository.path.read_text(encoding="utf-8")) == {
        "voice": "zh-CN-YunxiNeural",
        "rate": 12,
    }
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("rate", [-51, 51])
def test_settings_reject_rate_outside_supported_range(rate: int) -> None:
    with pytest.raises(ValueError, match="rate"):
        SpeechSettings(voice="zh-CN-XiaoxiaoNeural", rate=rate)


def test_settings_reject_voice_outside_chinese_allowlist() -> None:
    with pytest.raises(ValueError, match="voice"):
        SpeechSettings(voice="en-US-JennyNeural", rate=0)


def test_repository_recovers_to_defaults_when_local_file_is_invalid(
    tmp_path: Path,
) -> None:
    repository = SpeechSettingsRepository(tmp_path)
    repository.path.write_text("{broken", encoding="utf-8")

    assert repository.load() == DEFAULT_SPEECH_SETTINGS
