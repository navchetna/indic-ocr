"""PaddleOCR engine wrapper with lazy singleton pattern."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from paddleocr import PaddleOCR

from app.config import SUPPORTED_LANGUAGES, get_settings

logger = logging.getLogger(__name__)


class OCREngineManager:
    """Manages PaddleOCR engine instances — one per language, lazily loaded."""

    _engines: dict[str, PaddleOCR] = {}

    @classmethod
    def get_engine(cls, lang: str) -> PaddleOCR:
        """Get or create a PaddleOCR engine for the given language."""
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{lang}'. "
                f"Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        if lang not in cls._engines:
            logger.info(f"Loading PaddleOCR engine for language: {lang} ({SUPPORTED_LANGUAGES[lang]['name']})")
            start = time.time()

            # Initialize PaddleOCR with language-specific model
            cls._engines[lang] = PaddleOCR(
                lang=lang,
                enable_mkldnn=False,  # CPU stability: use pure Paddle inference (avoid MKL-DNN linking issues)
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

            elapsed = time.time() - start
            logger.info(f"PaddleOCR engine for '{lang}' loaded in {elapsed:.2f}s")

        return cls._engines[lang]

    @classmethod
    def loaded_languages(cls) -> list[str]:
        """Return list of currently loaded language codes."""
        return list(cls._engines.keys())

    @classmethod
    def preload(cls, languages: list[str]) -> None:
        """Preload engines for the specified languages."""
        for lang in languages:
            if lang in SUPPORTED_LANGUAGES:
                cls.get_engine(lang)
            else:
                logger.warning(f"Skipping preload for unsupported language: {lang}")


def run_ocr(image_input: str | Path, lang: str) -> dict[str, Any]:
    """
    Run OCR on a single image using official PaddleOCR v3.x API.

    Args:
        image_input: Path to an image file (str or Path).
        lang: Language code (hi, mr, te, ta).

    Returns:
        dict with keys:
            - results: list of {text, confidence, bounding_box}
            - full_text: concatenated recognized text (newline-separated)
    """
    engine = OCREngineManager.get_engine(lang)
    image_path = str(image_input)

    predictions = engine.predict(image_path)

    results = []
    text_lines = []

    for prediction in predictions:
        # PaddleOCR v3.x result object has these attributes:
        rec_texts = prediction.rec_texts if hasattr(prediction, "rec_texts") else []
        rec_scores = prediction.rec_scores if hasattr(prediction, "rec_scores") else []
        dt_polys = prediction.dt_polys if hasattr(prediction, "dt_polys") else []

        for i, text in enumerate(rec_texts):
            if text.strip():  # Skip empty text
                score = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                bbox = dt_polys[i].tolist() if i < len(dt_polys) else []

                results.append({
                    "text": text,
                    "confidence": round(score, 4),
                    "bounding_box": bbox,
                })
                text_lines.append(text)

    full_text = "\n".join(text_lines)
    return {"results": results, "full_text": full_text}


def _extract_results_from_saved_json(output_dir: Path) -> dict[str, Any]:
    """
    Extract OCR results from the JSON file saved by PaddleOCR.
    
    PaddleOCR saves a file like tmpXXXXX_res.json with rec_texts, rec_scores, rec_polys.
    
    Args:
        output_dir: Directory where PaddleOCR saved the JSON file.
    
    Returns:
        dict with results and full_text extracted from the saved JSON.
    """
    # Find the _res.json file in the output directory
    json_files = list(output_dir.glob("*_res.json"))
    
    if not json_files:
        logger.warning(f"No PaddleOCR JSON file found in {output_dir}")
        return {"results": [], "full_text": ""}
    
    json_file = json_files[0]  # Usually there's only one
    
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            ocr_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read PaddleOCR JSON file: {e}")
        return {"results": [], "full_text": ""}
    
    results = []
    text_lines = []
    
    rec_texts = ocr_data.get("rec_texts", [])
    rec_scores = ocr_data.get("rec_scores", [])
    rec_polys = ocr_data.get("rec_polys", [])
    
    for i, text in enumerate(rec_texts):
        if text.strip():  # Skip empty text
            score = float(rec_scores[i]) if i < len(rec_scores) else 0.0
            bbox = rec_polys[i] if i < len(rec_polys) else []
            
            results.append({
                "text": text,
                "confidence": round(score, 4),
                "bounding_box": bbox,
            })
            text_lines.append(text)
    
    full_text = "\n".join(text_lines)
    return {"results": results, "full_text": full_text}


def run_ocr_and_save_annotated(
    image_input: str | Path,
    lang: str,
    output_dir: Path,
) -> dict[str, Any]:
    """
    Run OCR on a single image and save all outputs.

    Uses the official PaddleOCR v3.x API for saving annotated images and JSON.
    Then reads the saved JSON to extract text results.

    Args:
        image_input: Path to an image file.
        lang: Language code.
        output_dir: Directory to save outputs to.

    Returns:
        dict with results (list of {text, confidence, bounding_box}) and full_text.
    """
    engine = OCREngineManager.get_engine(lang)
    image_path = str(image_input)

    predictions = engine.predict(image_path)

    output_dir_str = str(output_dir)

    # Save annotated image and detailed JSON using official PaddleOCR API
    for prediction in predictions:
        try:
            prediction.save_to_img(output_dir_str)
            prediction.save_to_json(output_dir_str)
        except Exception as e:
            logger.warning(f"Failed to save annotated image/JSON: {e}")

    # Extract results from the saved PaddleOCR JSON file
    ocr_result = _extract_results_from_saved_json(output_dir)
    
    logger.debug(f"Extracted {len(ocr_result['results'])} text regions from {output_dir}")
    
    return ocr_result
