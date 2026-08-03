from dataclasses import asdict, dataclass


CHINESE_EDGE_VOICES = (
    {
        "id": "zh-CN-XiaoxiaoNeural",
        "label": "晓晓 - 温暖自然女声",
        "gender": "female",
    },
    {
        "id": "zh-CN-XiaoyiNeural",
        "label": "晓伊 - 活力清晰女声",
        "gender": "female",
    },
    {
        "id": "zh-CN-YunxiNeural",
        "label": "云希 - 沉稳自然男声",
        "gender": "male",
    },
    {
        "id": "zh-CN-YunjianNeural",
        "label": "云健 - 新闻播报男声",
        "gender": "male",
    },
    {
        "id": "zh-CN-YunyangNeural",
        "label": "云扬 - 专业清晰男声",
        "gender": "male",
    },
)
CHINESE_EDGE_VOICE_IDS = frozenset(item["id"] for item in CHINESE_EDGE_VOICES)


@dataclass(frozen=True)
class SpeechSettings:
    voice: str
    rate: int

    def __post_init__(self) -> None:
        if self.voice not in CHINESE_EDGE_VOICE_IDS:
            raise ValueError("voice must be a supported Chinese Edge TTS voice")
        if isinstance(self.rate, bool) or not isinstance(self.rate, int):
            raise ValueError("rate must be an integer")
        if not -50 <= self.rate <= 50:
            raise ValueError("rate must be between -50 and 50")

    def model_dump(self) -> dict[str, str | int]:
        return asdict(self)

    @property
    def edge_rate(self) -> str:
        return f"{self.rate:+d}%"


DEFAULT_SPEECH_SETTINGS = SpeechSettings(
    voice="zh-CN-XiaoxiaoNeural",
    rate=0,
)
