"""Batch OCR endpoint — process all images in a server folder."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import SUPPORTED_LANGUAGES
from app.models.requests import BatchOCRRequest
from app.models.responses import BatchImageResult, BatchOCRResponse, TextRegion
from app.services.file_handler import (
    create_batch_output_dir,
    create_image_output_subdir,
    save_batch_summary,
    save_extracted_text,
    save_result_json,
)
from app.services.ocr_engine import run_ocr, run_ocr_and_save_annotated
from app.utils.image_utils import collect_images_from_folder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/batch", response_model=BatchOCRResponse)
async def ocr_batch(request: BatchOCRRequest):
    """
    Process all images in a server folder for OCR.

    Accepts an absolute path to a folder on the server and processes all
    supported image files found within.
    """
    lang = request.lang
    folder_path = request.folder_path

    # Validate language
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{lang}'. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}",
        )

    # Validate folder
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {folder_path}")

    # Collect images
    try:
        image_paths = collect_images_from_folder(folder, recursive=request.recursive)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not image_paths:
        raise HTTPException(
            status_code=400,
            detail=f"No supported image files found in folder: {folder_path}",
        )

    # Create batch output directory
    batch_output_dir = create_batch_output_dir(lang, folder_path)

    total_start = time.time()
    batch_results: list[BatchImageResult] = []
    processed_count = 0
    failed_count = 0

    logger.info(
        f"Starting batch OCR: {len(image_paths)} images | lang={lang} | "
        f"folder={folder_path}"
    )

    for image_path in image_paths:
        filename = image_path.name
        image_start = time.time()

        try:
            # Create per-image output subdirectory
            image_output_dir = create_image_output_subdir(batch_output_dir, filename)

            # Run OCR in a thread
            if request.save_annotated:
                ocr_result = await asyncio.to_thread(
                    run_ocr_and_save_annotated, image_path, lang, image_output_dir
                )
            else:
                ocr_result = await asyncio.to_thread(run_ocr, image_path, lang)

            image_time = round(time.time() - image_start, 3)

            text_regions = [
                TextRegion(
                    text=r["text"],
                    confidence=r["confidence"],
                    bounding_box=r["bounding_box"],
                )
                for r in ocr_result["results"]
            ]

            # Save per-image result files
            save_result_json(image_output_dir, {
                "filename": filename,
                "language": lang,
                "processing_time_seconds": image_time,
                "results": ocr_result["results"],
                "full_text": ocr_result["full_text"],
            })
            save_extracted_text(image_output_dir, ocr_result["full_text"])

            batch_results.append(
                BatchImageResult(
                    filename=filename,
                    success=True,
                    results=text_regions,
                    full_text=ocr_result["full_text"],
                    processing_time_seconds=image_time,
                )
            )
            processed_count += 1

            logger.debug(
                f"  Processed: {filename} | regions={len(text_regions)} | time={image_time}s"
            )

        except Exception as e:
            image_time = round(time.time() - image_start, 3)
            logger.warning(f"  Failed: {filename} | error={e}")
            batch_results.append(
                BatchImageResult(
                    filename=filename,
                    success=False,
                    error=str(e),
                    processing_time_seconds=image_time,
                )
            )
            failed_count += 1

    total_time = round(time.time() - total_start, 3)

    # Save batch summary
    summary_data = {
        "folder_path": folder_path,
        "language": lang,
        "total_images": len(image_paths),
        "processed": processed_count,
        "failed": failed_count,
        "processing_time_seconds": total_time,
        "results": [r.model_dump() for r in batch_results],
    }
    save_batch_summary(batch_output_dir, summary_data)

    logger.info(
        f"Batch OCR completed: {processed_count}/{len(image_paths)} processed | "
        f"failed={failed_count} | total_time={total_time}s"
    )

    return BatchOCRResponse(
        success=failed_count < len(image_paths),  # at least one success
        folder_path=folder_path,
        language=lang,
        output_dir=str(batch_output_dir),
        total_images=len(image_paths),
        processed=processed_count,
        failed=failed_count,
        processing_time_seconds=total_time,
        results=batch_results,
    )
