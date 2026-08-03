from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from qibao_api.speech.edge_tts_service import MAX_SPEECH_TEXT_LENGTH, EdgeTTSService
from qibao_api.speech.models import CHINESE_EDGE_VOICES, SpeechSettings
from qibao_api.speech.settings_repository import SpeechSettingsRepository


router = APIRouter(prefix="/api/v1/speech", tags=["speech"])


class SpeechSettingsView(BaseModel):
    voice: str
    rate: int


class VoiceView(BaseModel):
    id: str
    label: str
    gender: str


class VoiceCatalogView(BaseModel):
    voices: list[VoiceView]


def get_speech_settings_repository(request: Request) -> SpeechSettingsRepository:
    return request.app.state.speech_settings_repository


def get_edge_tts_service(request: Request) -> EdgeTTSService:
    return request.app.state.edge_tts_service


def _settings_view(settings: SpeechSettings) -> SpeechSettingsView:
    return SpeechSettingsView(**settings.model_dump())


@router.get("/settings", response_model=SpeechSettingsView)
def get_speech_settings(
    repository: Annotated[
        SpeechSettingsRepository, Depends(get_speech_settings_repository)
    ],
) -> SpeechSettingsView:
    return _settings_view(repository.load())


@router.put("/settings", response_model=SpeechSettingsView)
async def put_speech_settings(
    request: Request,
    repository: Annotated[
        SpeechSettingsRepository, Depends(get_speech_settings_repository)
    ],
) -> SpeechSettingsView:
    try:
        payload = await request.json()
        if not isinstance(payload, dict) or set(payload) != {"voice", "rate"}:
            raise ValueError("invalid shape")
        settings = SpeechSettings(voice=payload["voice"], rate=payload["rate"])
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Invalid speech settings") from error
    repository.save(settings)
    return _settings_view(settings)


@router.get("/voices", response_model=VoiceCatalogView)
def get_voice_catalog() -> VoiceCatalogView:
    return VoiceCatalogView(voices=[VoiceView(**item) for item in CHINESE_EDGE_VOICES])


@router.post("/synthesize", response_class=FileResponse)
async def synthesize_speech(
    request: Request,
    repository: Annotated[
        SpeechSettingsRepository, Depends(get_speech_settings_repository)
    ],
    service: Annotated[EdgeTTSService, Depends(get_edge_tts_service)],
) -> FileResponse:
    try:
        payload = await request.json()
        if not isinstance(payload, dict) or not set(payload).issubset(
            {"text", "voice", "rate"}
        ):
            raise ValueError("invalid shape")
        text = payload["text"]
        if not isinstance(text, str) or not text.strip() or len(text.strip()) > MAX_SPEECH_TEXT_LENGTH:
            raise ValueError("invalid text")
        saved = repository.load()
        settings = SpeechSettings(
            voice=payload.get("voice", saved.voice),
            rate=payload.get("rate", saved.rate),
        )
        audio_path = await service.synthesize(text, settings)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Invalid speech request") from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Speech synthesis unavailable") from error
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename="market-alert.mp3",
    )
