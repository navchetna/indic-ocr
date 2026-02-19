# IndicOCR Benchmarking

Benchmarking tool for evaluating the IndicOCR service against ground-truth datasets for Hindi and Telugu languages.

## Overview

The benchmark script sends images from the ground-truth training sets to the running IndicOCR API, measures performance metrics, and compares the OCR output against reference text files to compute accuracy.

### Metrics Measured

| Metric | Description |
|---|---|
| **Latency** | Time taken (seconds) for the API to process each image |
| **Average Confidence** | Mean of confidence scores returned by the OCR engine for each text region in an image |
| **Accuracy (CER)** | Character Error Rate — edit distance between OCR output and ground truth, normalized by ground-truth length. Accuracy = `1 - CER` |

## Dataset Layout

The script expects the following directory structure under `/user-ali/resources/ocr_inputs/`:

```
ocr_inputs/
├── hindi/
│   └── Page_Level_Training_Set/
│       ├── 10038.jpg
│       ├── 10038.txt      ← ground truth
│       ├── 10083.jpg
│       ├── 10083.txt
│       └── ...             (3500 image/text pairs)
└── telugu/
    └── Page_Level_Training_Set/
        ├── Page_Level_Training_Set1/
        │   ├── 21698.jpg
        │   ├── 21698.txt
        │   └── ...         (1437 image/text pairs)
        └── Page_Level_Training_Set2/
            ├── 10119.jpg
            ├── 10119.txt
            └── ...         (2059 image/text pairs)
```

Each `.txt` file contains the ground-truth text corresponding to its paired `.jpg` image.

## Prerequisites

- The IndicOCR service must be **running** (default: `http://localhost:8111`)
- Python 3.10+
- All dependencies are listed in the project's `requirements.txt`

## Usage

```bash
cd /user-ali/indicOCR
python -m benchmarks.benchmark [OPTIONS]
```

### CLI Flags

| Flag | Default | Description |
|---|---|---|
| `-n`, `--num-images` | `100` | Number of images to sample per language |
| `-l`, `--languages` | `hi,te` | Comma-separated language codes to benchmark |
| `-u`, `--user` | `default` | User identifier included in the run ID |
| `--api-url` | `http://localhost:8111` | Base URL of the IndicOCR API |
| `--output-dir` | `/user-ali/outputs/ocr/benchmarks` | Directory to save CSV results |
| `--seed` | `42` | Random seed for reproducible image sampling |

### Examples

**Benchmark 100 images for all languages (defaults):**

```bash
python -m benchmarks.benchmark
```

**Benchmark 50 Hindi images only:**

```bash
python -m benchmarks.benchmark -n 50 -l hi
```

**Benchmark with a specific user tag:**

```bash
python -m benchmarks.benchmark -u alice -n 200
```

**Use a different API endpoint:**

```bash
python -m benchmarks.benchmark --api-url http://10.0.0.5:8111
```

## Output

Each run produces **two CSV files** in the output directory:

```
outputs/ocr/benchmarks/
├── benchmark_20260219_143022_alice_details.csv   ← per-image results
└── benchmark_20260219_143022_alice_summary.csv   ← per-language aggregates
```

### Details CSV (`*_details.csv`) — Per-Image Results

| Column | Description |
|---|---|
| `run_id` | Unique run identifier (`YYYYMMDD_HHMMSS_user`) |
| `language` | Language code (`hi`, `te`) |
| `image_file` | Image filename |
| `ground_truth_file` | Ground-truth text filename |
| `latency_seconds` | API response time |
| `avg_confidence` | Mean confidence score across detected text regions |
| `accuracy` | `1 - CER` (character-level accuracy, 0.0–1.0) |
| `ocr_text_length` | Length of OCR output text |
| `ground_truth_length` | Length of ground-truth text |
| `status` | `success` or `error` |
| `error_message` | Error details (if any) |

### Summary CSV (`*_summary.csv`) — Per-Language Aggregates

| Column | Description |
|---|---|
| `run_id` | Unique run identifier |
| `language` | Language code |
| `images_requested` | Number of images requested via `-n` flag |
| `images_processed` | Actual images processed |
| `images_succeeded` | Successfully processed count |
| `images_failed` | Failed count |
| `seed` | Random seed used |
| `avg_latency_seconds` | Mean latency |
| `min_latency_seconds` | Fastest image |
| `max_latency_seconds` | Slowest image |
| `median_latency_seconds` | Median latency |
| `p95_latency_seconds` | 95th-percentile latency |
| `avg_accuracy` | Mean accuracy |
| `min_accuracy` | Lowest accuracy |
| `max_accuracy` | Highest accuracy |
| `median_accuracy` | Median accuracy |
| `avg_confidence` | Mean confidence score |
| `min_confidence` | Lowest confidence |
| `max_confidence` | Highest confidence |
| `avg_ocr_text_length` | Mean OCR output length |
| `avg_ground_truth_length` | Mean ground-truth text length |
| `total_run_time_seconds` | Total wall-clock time for the language |

A summary table is also printed to stdout at the end of each run.
