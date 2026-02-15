"""Pydantic request models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BatchOCRRequest(BaseModel):
    """Request body for batch OCR processing."""

    folder_path: str = Field(
        ...,
        description="Absolute path to the folder containing images on the server",
        examples=["/user-ali/resources/ocr_inputs/hindi/Page_Level_Training_Set"],
    )
    lang: str = Field(
        ...,
        description="Language code for OCR recognition",
        examples=["hi", "mr", "te", "ta"],
    )
    save_annotated: bool = Field(
        default=True,
        description="Whether to save annotated images with bounding boxes",
    )
    recursive: bool = Field(
        default=False,
        description="Whether to scan subfolders recursively",
    )
