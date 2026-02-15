"""Single-image OCR endpoint."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.config import SUPPORTED_LANGUAGES
from app.models.responses import SingleOCRResponse, TextRegion
from app.services.file_handler import (
    create_single_output_dir,
    save_extracted_text,
    save_result_json,
)
from app.services.ocr_engine import run_ocr, run_ocr_and_save_annotated
from app.utils.image_utils import validate_image_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/single", response_model=SingleOCRResponse)
async def ocr_single_image(
    file: UploadFile = File(..., description="Image file to process"),
    lang: str = Query(..., description="Language code: hi, mr, te, ta"),
    save_annotated: bool = Query(True, description="Save annotated image with bounding boxes"),
):
    """
    Process a single uploaded image for OCR.

    Accepts an image file via multipart form upload and returns recognized text
    with bounding boxes and confidence scores.
    """
    # Validate language
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{lang}'. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}",
        )

    # Read and validate the uploaded file
    try:
        image_data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    try:
        validate_image_bytes(image_data, file.filename or "unknown.png")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create output directory
    filename = file.filename or "unknown.png"
    output_dir = create_single_output_dir(lang, filename)

    # Write uploaded file to a temp location for PaddleOCR
    tmp_path = None
    try:
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_data)
            tmp_path = Path(tmp.name)

        start_time = time.time()

        # Run OCR in a thread to avoid blocking the event loop
        if save_annotated:
            ocr_result = await asyncio.to_thread(
                run_ocr_and_save_annotated, tmp_path, lang, output_dir
            )
        else:
            ocr_result = await asyncio.to_thread(run_ocr, tmp_path, lang)

        processing_time = round(time.time() - start_time, 3)

        # Build response
        text_regions = [
            TextRegion(
                text=r["text"],
                confidence=r["confidence"],
                bounding_box=r["bounding_box"],
            )
            for r in ocr_result["results"]
        ]

        # Save result files
        save_result_json(output_dir, {
            "filename": filename,
            "language": lang,
            "processing_time_seconds": processing_time,
            "results": ocr_result["results"],
            "full_text": ocr_result["full_text"],
        })
        save_extracted_text(output_dir, ocr_result["full_text"])

        logger.info(
            f"Single OCR completed: {filename} | lang={lang} | "
            f"regions={len(text_regions)} | time={processing_time}s"
        )

        return SingleOCRResponse(
            success=True,
            filename=filename,
            language=lang,
            output_dir=str(output_dir),
            results=text_regions,
            full_text=ocr_result["full_text"],
            processing_time_seconds=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"OCR processing failed for {filename}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {e}")
    finally:
        # Clean up temp file
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
