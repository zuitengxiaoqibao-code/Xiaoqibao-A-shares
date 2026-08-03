from pathlib import Path

import pytest

from qibao_api.speech.edge_tts_service import EdgeTTSService
from qibao_api.speech.models import SpeechSettings


class FakeCommunicator:
    def __init__(self, calls: list[tuple[str, str, str]], text: str, voice: str, rate: str) -> None:
        self.calls = calls
        self.arguments = (text, voice, rate)

    async def save(self, path: str) -> None:
        self.calls.append(self.arguments)
        Path(path).write_bytes(b"ID3-real-audio")


@pytest.mark.asyncio
async def test_synthesis_writes_mp3_to_dedicated_cache_and_reuses_it(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str, str]] = []

    def factory(text: str, voice: str, rate: str) -> FakeCommunicator:
        return FakeCommunicator(calls, text, voice, rate)

    service = EdgeTTSService(tmp_path / "cache" / "tts", communicator_factory=factory)
    settings = SpeechSettings(voice="zh-CN-XiaoxiaoNeural", rate=8)

    first = await service.synthesize("  浦发银行 盘中放量上涨  ", settings)
    second = await service.synthesize("浦发银行 盘中放量上涨", settings)

    assert first == second
    assert first.parent == tmp_path / "cache" / "tts"
    assert first.suffix == ".mp3"
    assert first.read_bytes() == b"ID3-real-audio"
    assert calls == [("浦发银行 盘中放量上涨", "zh-CN-XiaoxiaoNeural", "+8%")]


@pytest.mark.asyncio
async def test_cache_key_changes_with_voice_and_rate(tmp_path: Path) -> None:
    calls: list[tuple[str, str, str]] = []

    def factory(text: str, voice: str, rate: str) -> FakeCommunicator:
        return FakeCommunicator(calls, text, voice, rate)

    service = EdgeTTSService(tmp_path, communicator_factory=factory)

    first = await service.synthesize(
        "测试播报", SpeechSettings(voice="zh-CN-XiaoxiaoNeural", rate=0)
    )
    second = await service.synthesize(
        "测试播报", SpeechSettings(voice="zh-CN-YunxiNeural", rate=-10)
    )

    assert first != second
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_synthesis_rejects_blank_or_excessive_text(tmp_path: Path) -> None:
    service = EdgeTTSService(tmp_path, communicator_factory=lambda *_args: None)
    settings = SpeechSettings(voice="zh-CN-XiaoxiaoNeural", rate=0)

    with pytest.raises(ValueError, match="text"):
        await service.synthesize("   ", settings)
    with pytest.raises(ValueError, match="text"):
        await service.synthesize("测" * 501, settings)
