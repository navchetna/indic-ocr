"""Pydantic response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TextRegion(BaseModel):
    """A single detected text region with its OCR result."""

    text: str = Field(..., description="Recognized text")
    confidence: float = Field(..., description="Recognition confidence score (0-1)")
    bounding_box: list[list[float]] = Field(
        ..., description="Polygon bounding box as list of [x, y] points"
    )


class SingleOCRResponse(BaseModel):
    """Response for single-image OCR processing."""

    success: bool
    filename: str
    language: str
    extracted_text: str = Field(..., description="All recognized text concatenated")
    processing_time_seconds: float


class BatchImageResult(BaseModel):
    """Result for a single image within a batch."""

    filename: str
    success: bool
    results: list[TextRegion] = []
    full_text: str = ""
    error: str | None = None
    processing_time_seconds: float = 0.0


class BatchOCRResponse(BaseModel):
    """Response for batch OCR processing."""

    success: bool
    folder_path: str
    language: str
    output_dir: str
    total_images: int
    processed: int
    failed: int
    processing_time_seconds: float
    results: list[BatchImageResult]


class LanguageInfo(BaseModel):
    """Information about a supported language."""

    code: str
    name: str
    script: str


class LanguagesResponse(BaseModel):
    """Response listing supported languages."""

    languages: list[LanguageInfo]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    loaded_languages: list[str]
    detection_model: str
    version: str
