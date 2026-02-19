"""
IndicOCR Benchmarking Script

Benchmarks the IndicOCR API against ground-truth datasets for Hindi and Telugu,
measuring latency, average confidence, and character-level accuracy.

Usage:
    python -m benchmarks.benchmark [OPTIONS]

Run `python -m benchmarks.benchmark --help` for all options.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

try:
    from rapidfuzz.distance import Levenshtein as RFLevenshtein

    _USE_RAPIDFUZZ = True
except ImportError:
    _USE_RAPIDFUZZ = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_NUM_IMAGES = 100
DEFAULT_API_URL = "http://localhost:8111"
DEFAULT_OUTPUT_DIR = "/user-ali/outputs/ocr/benchmarks"
DEFAULT_INPUT_BASE = "/user-ali/resources/ocr_inputs"
DEFAULT_USER = "default"
DEFAULT_SEED = 42

# Language → list of directories containing paired .jpg/.txt files
LANGUAGE_DATASET_DIRS: dict[str, list[str]] = {
    "hi": [
        "{input_base}/hindi/Page_Level_Training_Set",
    ],
    "te": [
        "{input_base}/telugu/Page_Level_Training_Set/Page_Level_Training_Set1",
        "{input_base}/telugu/Page_Level_Training_Set/Page_Level_Training_Set2",
    ],
}

# Language code → API language parameter
LANG_CODE_MAP: dict[str, str] = {
    "hi": "hi",
    "te": "te",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ImageSample:
    """An image paired with its ground-truth text file."""

    image_path: Path
    ground_truth_path: Path
    language: str


@dataclass
class BenchmarkResult:
    """Result of benchmarking a single image."""

    run_id: str
    language: str
    image_file: str
    ground_truth_file: str
    latency_seconds: float = 0.0
    avg_confidence: float = 0.0
    accuracy: float = 0.0
    ocr_text_length: int = 0
    ground_truth_length: int = 0
    status: str = "success"
    error_message: str = ""


# ---------------------------------------------------------------------------
# Accuracy helpers
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Normalize text to a single line: collapse all whitespace, strip edges.

    Ground-truth files store text on a single line, so OCR output must be
    flattened the same way before comparison.
    """
    return " ".join(text.split())


def compute_cer(ocr_text: str, ground_truth: str) -> float:
    """
    Compute Character Error Rate between OCR output and ground truth.

    CER = edit_distance(ocr, gt) / len(gt)
    Returns 1.0 if ground truth is empty.
    """
    ocr_norm = _normalize_text(ocr_text)
    gt_norm = _normalize_text(ground_truth)

    if not gt_norm:
        return 1.0

    if _USE_RAPIDFUZZ:
        dist = RFLevenshtein.distance(ocr_norm, gt_norm)
    else:
        dist = _levenshtein_fallback(ocr_norm, gt_norm)

    return min(dist / len(gt_norm), 1.0)


def _levenshtein_fallback(s1: str, s2: str) -> int:
    """Pure-Python Levenshtein distance (slow, used when library unavailable)."""
    if len(s1) < len(s2):
        return _levenshtein_fallback(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


# ---------------------------------------------------------------------------
# Dataset discovery
# ---------------------------------------------------------------------------


def discover_samples(
    language: str,
    input_base: str,
) -> list[ImageSample]:
    """
    Discover all image/ground-truth pairs for a language.

    Returns a list of ImageSample, each pointing to a .jpg and its matching .txt.
    """
    dirs_templates = LANGUAGE_DATASET_DIRS.get(language)
    if dirs_templates is None:
        logger.warning(f"No dataset configured for language '{language}'. Skipping.")
        return []

    samples: list[ImageSample] = []
    for dir_template in dirs_templates:
        dir_path = Path(dir_template.format(input_base=input_base))
        if not dir_path.is_dir():
            logger.warning(f"Dataset directory not found: {dir_path}")
            continue

        for img_file in sorted(dir_path.glob("*.jpg")):
            txt_file = img_file.with_suffix(".txt")
            if txt_file.exists():
                samples.append(
                    ImageSample(
                        image_path=img_file,
                        ground_truth_path=txt_file,
                        language=language,
                    )
                )

    logger.info(f"[{language}] Found {len(samples)} image/ground-truth pairs")
    return samples


# ---------------------------------------------------------------------------
# API interaction
# ---------------------------------------------------------------------------


def call_ocr_api(
    api_url: str,
    image_path: Path,
    lang: str,
) -> dict:
    """
    Call the IndicOCR single-image endpoint.

    Returns dict with keys: extracted_text, processing_time_seconds,
    and the raw response JSON.
    """
    url = f"{api_url}/ocr/single"
    api_lang = LANG_CODE_MAP.get(lang, lang)

    with open(image_path, "rb") as f:
        files = {"file": (image_path.name, f, "image/jpeg")}
        params = {"lang": api_lang, "save_annotated": "false"}

        start = time.perf_counter()
        resp = requests.post(url, files=files, params=params, timeout=120)
        latency = time.perf_counter() - start

    resp.raise_for_status()
    data = resp.json()
    data["_measured_latency"] = round(latency, 4)
    return data


# ---------------------------------------------------------------------------
# Single-image benchmark
# ---------------------------------------------------------------------------


def benchmark_single(
    sample: ImageSample,
    api_url: str,
    run_id: str,
) -> BenchmarkResult:
    """Benchmark a single image against its ground truth."""
    result = BenchmarkResult(
        run_id=run_id,
        language=sample.language,
        image_file=sample.image_path.name,
        ground_truth_file=sample.ground_truth_path.name,
    )

    # Read ground truth
    try:
        gt_text = sample.ground_truth_path.read_text(encoding="utf-8")
    except Exception as e:
        result.status = "error"
        result.error_message = f"Failed to read ground truth: {e}"
        return result

    result.ground_truth_length = len(_normalize_text(gt_text))

    # Call OCR API
    try:
        api_resp = call_ocr_api(api_url, sample.image_path, sample.language)
    except requests.exceptions.RequestException as e:
        result.status = "error"
        result.error_message = f"API request failed: {e}"
        return result
    except Exception as e:
        result.status = "error"
        result.error_message = f"Unexpected error: {e}"
        return result

    # Extract metrics
    ocr_text = api_resp.get("extracted_text", "")
    result.ocr_text_length = len(_normalize_text(ocr_text))
    result.latency_seconds = round(api_resp.get("_measured_latency", 0.0), 4)

    # Compute average confidence from text_regions in the API response
    text_regions = api_resp.get("text_regions", [])
    if text_regions:
        confidences = [r.get("confidence", 0.0) for r in text_regions]
        result.avg_confidence = round(sum(confidences) / len(confidences), 4)
    else:
        result.avg_confidence = -1.0  # no regions detected

    # Accuracy
    cer = compute_cer(ocr_text, gt_text)
    result.accuracy = round(1.0 - cer, 4)

    return result


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------


def run_benchmark(
    languages: list[str],
    num_images: int,
    api_url: str,
    output_dir: str,
    user: str,
    input_base: str,
    seed: int,
) -> Path:
    """
    Run the full benchmark across specified languages.

    Returns the path to the generated CSV file.
    """
    # Generate run ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{timestamp}_{user}"

    logger.info(f"Starting benchmark run: {run_id}")
    logger.info(f"Languages: {languages} | Images per lang: {num_images} | Seed: {seed}")
    logger.info(f"API URL: {api_url}")

    # Ensure output directory exists
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    details_csv = out_path / f"benchmark_{run_id}_details.csv"
    summary_csv = out_path / f"benchmark_{run_id}_summary.csv"

    all_results: list[BenchmarkResult] = []

    for lang in languages:
        logger.info(f"\n{'='*60}")
        logger.info(f"Benchmarking language: {lang}")
        logger.info(f"{'='*60}")

        # Discover samples
        samples = discover_samples(lang, input_base)
        if not samples:
            logger.warning(f"No samples found for language '{lang}'. Skipping.")
            continue

        # Sample images
        rng = random.Random(seed)
        n = min(num_images, len(samples))
        selected = rng.sample(samples, n)
        logger.info(f"[{lang}] Selected {n} images for benchmarking")

        for idx, sample in enumerate(selected, 1):
            logger.info(
                f"  [{lang}] Processing {idx}/{n}: {sample.image_path.name}"
            )
            result = benchmark_single(sample, api_url, run_id)
            all_results.append(result)

            if result.status == "error":
                logger.warning(
                    f"  [{lang}] ERROR on {sample.image_path.name}: "
                    f"{result.error_message}"
                )
            else:
                logger.info(
                    f"  [{lang}] {sample.image_path.name} | "
                    f"latency={result.latency_seconds}s | "
                    f"accuracy={result.accuracy:.4f} | "
                    f"confidence={result.avg_confidence}"
                )

    # Write CSVs
    if all_results:
        _write_details_csv(details_csv, all_results)
        logger.info(f"\nDetailed results saved to: {details_csv}")

        _write_summary_csv(summary_csv, all_results, run_id, num_images, seed)
        logger.info(f"Summary results saved to:  {summary_csv}")

        # Print summary to console
        _print_summary(all_results)
    else:
        logger.warning("No results to write.")

    return details_csv


def _write_details_csv(csv_file: Path, results: list[BenchmarkResult]) -> None:
    """Write per-image granular benchmark results to a CSV file."""
    fieldnames = [
        "run_id",
        "language",
        "image_file",
        "ground_truth_file",
        "latency_seconds",
        "avg_confidence",
        "accuracy",
        "ocr_text_length",
        "ground_truth_length",
        "status",
        "error_message",
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "run_id": r.run_id,
                    "language": r.language,
                    "image_file": r.image_file,
                    "ground_truth_file": r.ground_truth_file,
                    "latency_seconds": r.latency_seconds,
                    "avg_confidence": r.avg_confidence,
                    "accuracy": r.accuracy,
                    "ocr_text_length": r.ocr_text_length,
                    "ground_truth_length": r.ground_truth_length,
                    "status": r.status,
                    "error_message": r.error_message,
                }
            )


def _write_summary_csv(
    csv_file: Path,
    results: list[BenchmarkResult],
    run_id: str,
    num_images_requested: int,
    seed: int,
) -> None:
    """Write consolidated per-language summary to a separate CSV file."""
    from collections import defaultdict

    by_lang: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for r in results:
        by_lang[r.language].append(r)

    fieldnames = [
        "run_id",
        "language",
        "images_requested",
        "images_processed",
        "images_succeeded",
        "images_failed",
        "seed",
        "avg_latency_seconds",
        "min_latency_seconds",
        "max_latency_seconds",
        "median_latency_seconds",
        "p95_latency_seconds",
        "avg_accuracy",
        "min_accuracy",
        "max_accuracy",
        "median_accuracy",
        "avg_confidence",
        "min_confidence",
        "max_confidence",
        "avg_ocr_text_length",
        "avg_ground_truth_length",
        "total_run_time_seconds",
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for lang, lang_results in sorted(by_lang.items()):
            ok = [r for r in lang_results if r.status == "success"]
            fail_count = len(lang_results) - len(ok)

            latencies = sorted(r.latency_seconds for r in ok) if ok else [0.0]
            accuracies = sorted(r.accuracy for r in ok) if ok else [0.0]
            confidences = [r.avg_confidence for r in ok if r.avg_confidence >= 0]

            def _median(vals: list[float]) -> float:
                n = len(vals)
                if n == 0:
                    return 0.0
                mid = n // 2
                return (vals[mid] + vals[mid - 1]) / 2 if n % 2 == 0 else vals[mid]

            def _percentile(vals: list[float], pct: float) -> float:
                if not vals:
                    return 0.0
                k = (len(vals) - 1) * pct / 100.0
                lo = int(k)
                hi = min(lo + 1, len(vals) - 1)
                frac = k - lo
                return vals[lo] + frac * (vals[hi] - vals[lo])

            total_time = sum(r.latency_seconds for r in lang_results)

            writer.writerow(
                {
                    "run_id": run_id,
                    "language": lang,
                    "images_requested": num_images_requested,
                    "images_processed": len(lang_results),
                    "images_succeeded": len(ok),
                    "images_failed": fail_count,
                    "seed": seed,
                    "avg_latency_seconds": round(sum(latencies) / len(latencies), 4) if latencies else 0,
                    "min_latency_seconds": round(latencies[0], 4),
                    "max_latency_seconds": round(latencies[-1], 4),
                    "median_latency_seconds": round(_median(latencies), 4),
                    "p95_latency_seconds": round(_percentile(latencies, 95), 4),
                    "avg_accuracy": round(sum(accuracies) / len(accuracies), 4) if accuracies else 0,
                    "min_accuracy": round(accuracies[0], 4),
                    "max_accuracy": round(accuracies[-1], 4),
                    "median_accuracy": round(_median(accuracies), 4),
                    "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else -1,
                    "min_confidence": round(min(confidences), 4) if confidences else -1,
                    "max_confidence": round(max(confidences), 4) if confidences else -1,
                    "avg_ocr_text_length": round(sum(r.ocr_text_length for r in ok) / len(ok), 1) if ok else 0,
                    "avg_ground_truth_length": round(sum(r.ground_truth_length for r in ok) / len(ok), 1) if ok else 0,
                    "total_run_time_seconds": round(total_time, 2),
                }
            )


def _print_summary(results: list[BenchmarkResult]) -> None:
    """Print per-language aggregate summary to stdout."""
    from collections import defaultdict

    by_lang: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for r in results:
        by_lang[r.language].append(r)

    print("\n" + "=" * 72)
    print("BENCHMARK SUMMARY")
    print("=" * 72)
    print(
        f"{'Language':<10} {'Total':>6} {'OK':>6} {'Fail':>6} "
        f"{'Avg Latency':>12} {'Avg Accuracy':>13} {'Avg Confidence':>15}"
    )
    print("-" * 72)

    for lang, lang_results in sorted(by_lang.items()):
        ok_results = [r for r in lang_results if r.status == "success"]
        fail_count = len(lang_results) - len(ok_results)

        avg_latency = (
            sum(r.latency_seconds for r in ok_results) / len(ok_results)
            if ok_results
            else 0.0
        )
        avg_accuracy = (
            sum(r.accuracy for r in ok_results) / len(ok_results)
            if ok_results
            else 0.0
        )
        # Only compute avg confidence if any value is >= 0
        valid_conf = [r.avg_confidence for r in ok_results if r.avg_confidence >= 0]
        avg_conf = sum(valid_conf) / len(valid_conf) if valid_conf else -1.0
        conf_str = f"{avg_conf:.4f}" if avg_conf >= 0 else "N/A"

        print(
            f"{lang:<10} {len(lang_results):>6} {len(ok_results):>6} "
            f"{fail_count:>6} {avg_latency:>11.3f}s {avg_accuracy:>12.4f} "
            f"{conf_str:>15}"
        )

    print("=" * 72)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="indicocr-benchmark",
        description="Benchmark IndicOCR against ground-truth datasets.",
    )
    parser.add_argument(
        "-n",
        "--num-images",
        type=int,
        default=DEFAULT_NUM_IMAGES,
        help=f"Number of images to sample per language (default: {DEFAULT_NUM_IMAGES})",
    )
    parser.add_argument(
        "-l",
        "--languages",
        type=str,
        default="hi,te",
        help="Comma-separated language codes to benchmark (default: hi,te)",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        default=DEFAULT_USER,
        help=f"User identifier for run ID (default: {DEFAULT_USER})",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=DEFAULT_API_URL,
        help=f"Base URL of the IndicOCR API (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save CSV results (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--input-base",
        type=str,
        default=DEFAULT_INPUT_BASE,
        help=f"Base directory for input datasets (default: {DEFAULT_INPUT_BASE})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducible sampling (default: {DEFAULT_SEED})",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = parse_args(argv)
    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]

    if not languages:
        logger.error("No languages specified.")
        sys.exit(1)

    # Validate languages
    valid_langs = set(LANGUAGE_DATASET_DIRS.keys())
    for lang in languages:
        if lang not in valid_langs:
            logger.error(
                f"Unsupported language '{lang}'. Supported: {', '.join(sorted(valid_langs))}"
            )
            sys.exit(1)

    csv_path = run_benchmark(
        languages=languages,
        num_images=args.num_images,
        api_url=args.api_url,
        output_dir=args.output_dir,
        user=args.user,
        input_base=args.input_base,
        seed=args.seed,
    )

    print(f"\nBenchmark complete. Results: {csv_path}")


if __name__ == "__main__":
    main()
