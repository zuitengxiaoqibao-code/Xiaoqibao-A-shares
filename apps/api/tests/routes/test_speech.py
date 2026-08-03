from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.routes.speech import router
from qibao_api.speech.models import SpeechSettings
from qibao_api.speech.settings_repository import SpeechSettingsRepository


class SpeechService:
    def __init__(self, audio_path: Path) -> None:
        self.audio_path = audio_path
        self.calls: list[tuple[str, SpeechSettings]] = []

    async def synthesize(self, text: str, settings: SpeechSettings) -> Path:
        self.calls.append((text, settings))
        self.audio_path.write_bytes(b"ID3-route-audio")
        return self.audio_path


def client(tmp_path: Path) -> tuple[TestClient, SpeechService]:
    application = FastAPI()
    application.state.speech_settings_repository = SpeechSettingsRepository(tmp_path)
    service = SpeechService(tmp_path / "speech.mp3")
    application.state.edge_tts_service = service
    application.include_router(router)
    return TestClient(application), service


def test_settings_and_voice_catalog_are_available(tmp_path: Path) -> None:
    subject, _service = client(tmp_path)

    defaults = subject.get("/api/v1/speech/settings")
    voices = subject.get("/api/v1/speech/voices")

    assert defaults.status_code == 200
    assert defaults.json() == {"voice": "zh-CN-XiaoxiaoNeural", "rate": 0}
    assert voices.status_code == 200
    assert any(item["id"] == "zh-CN-XiaoxiaoNeural" for item in voices.json()["voices"])


def test_put_settings_persists_valid_voice_and_rate(tmp_path: Path) -> None:
    subject, _service = client(tmp_path)

    response = subject.put(
        "/api/v1/speech/settings",
        json={"voice": "zh-CN-YunxiNeural", "rate": -15},
    )

    assert response.status_code == 200
    assert subject.get("/api/v1/speech/settings").json() == {
        "voice": "zh-CN-YunxiNeural",
        "rate": -15,
    }


def test_put_settings_rejects_unknown_fields_and_invalid_values(tmp_path: Path) -> None:
    subject, _service = client(tmp_path)

    unexpected = subject.put(
        "/api/v1/speech/settings",
        json={"voice": "zh-CN-XiaoxiaoNeural", "rate": 0, "enabled": True},
    )
    invalid = subject.put(
        "/api/v1/speech/settings",
        json={"voice": "en-US-JennyNeural", "rate": 100},
    )

    assert unexpected.status_code == 422
    assert invalid.status_code == 422


def test_synthesize_returns_playable_mpeg_using_saved_settings(tmp_path: Path) -> None:
    subject, service = client(tmp_path)
    subject.put(
        "/api/v1/speech/settings",
        json={"voice": "zh-CN-YunxiNeural", "rate": 10},
    )

    response = subject.post(
        "/api/v1/speech/synthesize",
        json={"text": "宁德时代出现盘中异动"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content == b"ID3-route-audio"
    assert service.calls == [
        (
            "宁德时代出现盘中异动",
            SpeechSettings(voice="zh-CN-YunxiNeural", rate=10),
        )
    ]


def test_synthesize_accepts_preview_override_without_saving_it(tmp_path: Path) -> None:
    subject, service = client(tmp_path)

    response = subject.post(
        "/api/v1/speech/synthesize",
        json={
            "text": "这是一段试听语音",
            "voice": "zh-CN-YunxiNeural",
            "rate": -20,
        },
    )

    assert response.status_code == 200
    assert service.calls[-1][1] == SpeechSettings(
        voice="zh-CN-YunxiNeural", rate=-20
    )
    assert subject.get("/api/v1/speech/settings").json()["voice"] == (
        "zh-CN-XiaoxiaoNeural"
    )


def test_synthesize_rejects_invalid_shape_and_long_text(tmp_path: Path) -> None:
    subject, _service = client(tmp_path)

    invalid_shape = subject.post(
        "/api/v1/speech/synthesize", json={"text": "测试", "extra": True}
    )
    long_text = subject.post(
        "/api/v1/speech/synthesize", json={"text": "测" * 501}
    )

    assert invalid_shape.status_code == 422
    assert long_text.status_code == 422
