"""File I/O and output directory management."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


def create_single_output_dir(lang: str, filename: str) -> Path:
    """
    Create an output directory for a single-image OCR result.

    Structure: {base}/single/{lang}/{timestamp}_{filestem}/
    """
    settings = get_settings()
    filestem = Path(filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{timestamp}_{filestem}"
    output_dir = settings.single_output_dir / lang / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def create_batch_output_dir(lang: str, folder_path: str) -> Path:
    """
    Create an output directory for a batch OCR result.

    Structure: {base}/batch/{lang}/{timestamp}_{foldername}/
    """
    settings = get_settings()
    folder_name = Path(folder_path).name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{timestamp}_{folder_name}"
    output_dir = settings.batch_output_dir / lang / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def create_image_output_subdir(batch_dir: Path, filename: str) -> Path:
    """Create a subdirectory for a single image within a batch output dir."""
    filestem = Path(filename).stem
    subdir = batch_dir / filestem
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def save_result_json(output_dir: Path, data: dict) -> Path:
    """Save OCR result as JSON."""
    output_path = output_dir / "result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug(f"Saved result JSON: {output_path}")
    return output_path


def save_extracted_text(output_dir: Path, text: str) -> Path:
    """Save extracted text as plain text file."""
    output_path = output_dir / "extracted_text.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.debug(f"Saved extracted text: {output_path}")
    return output_path


def save_batch_summary(output_dir: Path, summary: dict) -> Path:
    """Save batch processing summary as JSON."""
    output_path = output_dir / "batch_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.debug(f"Saved batch summary: {output_path}")
    return output_path
