"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import batch, health, ocr
from app.services.ocr_engine import OCREngineManager
from app.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: run startup and shutdown logic."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("IndicOCR service starting up...")
    logger.info(f"Output base directory: {settings.ocr_output_base}")
    logger.info(f"Platform: Intel Xeon 6 (CPU-based inference, stable PaddleOCR v3.x)")

    # Preload requested languages
    preload = settings.preload_language_list
    if preload:
        logger.info(f"Preloading languages: {preload}")
        OCREngineManager.preload(preload)
    else:
        logger.info("No languages preloaded (will load on first request)")

    yield

    logger.info("IndicOCR service shutting down.")


app = FastAPI(
    title="IndicOCR",
    description=(
        "OCR service for extracting text from handwritten document images in "
        "Indic languages (Hindi, Marathi, Telugu, Tamil) powered by PaddleOCR PP-OCRv5."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(ocr.router)
app.include_router(batch.router)
