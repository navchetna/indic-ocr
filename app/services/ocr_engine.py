"""PaddleOCR engine wrapper with lazy singleton pattern."""

from __future__ import annotations

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
            # Using simple initialization that works reliably (based on /user-ali/indic.ai/paddleOCR/PaddleOCR/inference/run.py)
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
    Run OCR on a single image.

    Args:
        image_input: Path to an image file (str or Path).
        lang: Language code (hi, mr, te, ta).

    Returns:
        dict with keys:
            - results: list of {text, confidence, bounding_box}
            - full_text: concatenated recognized text
    """
    engine = OCREngineManager.get_engine(lang)
    image_path = str(image_input)

    predictions = engine.predict(image_path)

    results = []
    text_lines = []

    for prediction in predictions:
        # Each prediction has rec_texts, rec_scores, dt_polys
        rec_texts = getattr(prediction, "rec_texts", []) or []
        rec_scores = getattr(prediction, "rec_scores", []) or []
        dt_polys = getattr(prediction, "dt_polys", []) or []

        for i, text in enumerate(rec_texts):
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


def run_ocr_and_save_annotated(
    image_input: str | Path,
    lang: str,
    output_dir: Path,
) -> dict[str, Any]:
    """
    Run OCR on a single image and save the annotated image.

    Args:
        image_input: Path to an image file.
        lang: Language code.
        output_dir: Directory to save annotated image to.

    Returns:
        Same as run_ocr, plus saves annotated image.
    """
    engine = OCREngineManager.get_engine(lang)
    image_path = str(image_input)

    predictions = engine.predict(image_path)

    results = []
    text_lines = []

    for prediction in predictions:
        rec_texts = getattr(prediction, "rec_texts", []) or []
        rec_scores = getattr(prediction, "rec_scores", []) or []
        dt_polys = getattr(prediction, "dt_polys", []) or []

        # Save annotated image
        try:
            prediction.save_to_img(str(output_dir))
        except Exception as e:
            logger.warning(f"Failed to save annotated image: {e}")

        for i, text in enumerate(rec_texts):
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
