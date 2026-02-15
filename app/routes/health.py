"""Health check and language listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import SUPPORTED_LANGUAGES, get_settings
from app.models.responses import HealthResponse, LanguageInfo, LanguagesResponse
from app.services.ocr_engine import OCREngineManager

router = APIRouter(tags=["Health"])

APP_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and loaded model info."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        loaded_languages=OCREngineManager.loaded_languages(),
        detection_model=settings.detection_model,
        version=APP_VERSION,
    )


@router.get("/ocr/languages", response_model=LanguagesResponse)
async def list_languages():
    """List all supported languages."""
    languages = [
        LanguageInfo(code=code, name=info["name"], script=info["script"])
        for code, info in SUPPORTED_LANGUAGES.items()
    ]
    return LanguagesResponse(languages=languages)
