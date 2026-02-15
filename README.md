# IndicOCR

> **Platform:** This application is specifically designed to run on **Intel Xeon 6** processors with CPU-based inference.

A FastAPI-based OCR service for extracting text from handwritten document images in Indic languages, powered by **PaddleOCR PP-OCRv5**.

## Features

- **Multi-language support** — Hindi (`hi`), Marathi (`mr`), Telugu (`te`), Tamil (`ta`)
- **Single image processing** — Upload an image file via multipart form
- **Batch processing** — Point to a folder on the server and process all images
- **Rich output** — JSON results with bounding boxes, plain extracted text, and annotated images
- **Language-agnostic API** — Same endpoints for all languages; pass the language code as a parameter
- **Lazy model loading** — Models load on first request per language; cached for subsequent calls
- **Docker ready** — Dockerfile and docker-compose included

## Quick Start

### Prerequisites

- Python 3.10+
- PaddlePaddle CPU variant

### Install & Run Locally

```bash
cd indicOCR

# Setup environment
cp .env.example .env
# Edit .env and update HOME_DIR, OCR_OUTPUT_BASE, and OCR_INPUT_BASE for your machine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8111 --reload
```

The API is available at **http://localhost:8111**. Interactive docs at **http://localhost:8111/docs**.

### Run with Docker

```bash
cd indicOCR

# Setup environment
cp .env.example .env
# Edit .env and update HOME_DIR, OCR_OUTPUT_BASE, and OCR_INPUT_BASE for your machine

# Build and start (uses .env file for paths)
docker compose up --build -d

# Check logs
docker compose logs -f indicocr
```

---

## API Reference

### Health Check

```
GET /health
```

Returns service status such as loaded languages.

### Supported Languages

```
GET /ocr/languages
```

Returns the list of supported languages, their codes, and scripts.

### Single Image OCR

```
POST /ocr/single?lang=hi&save_annotated=true
```

Upload one image via multipart form:

```bash
curl -X POST "http://localhost:8111/ocr/single?lang=hi" \
  -F "file=@/path/to/document.png"
```

**Parameters:**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `file` | body (form) | file | Yes | Image file (PNG, JPG, JPEG, TIFF, BMP, WEBP) |
| `lang` | query | string | Yes | Language code: `hi`, `mr`, `te`, `ta` |
| `save_annotated` | query | bool | No | Save annotated image (default: `true`) |

**Response** (JSON):

```json
{
  "success": true,
  "filename": "document.png",
  "language": "hi",
  "output_dir": "${OCR_OUTPUT_BASE}/single/hi/20260215_143022_document",
  "results": [
    {
      "text": "नमस्ते दुनिया",
      "confidence": 0.9523,
      "bounding_box": [[10, 20], [200, 20], [200, 60], [10, 60]]
    }
  ],
  "full_text": "नमस्ते दुनिया\nयह एक परीक्षण है",
  "processing_time_seconds": 2.34
}
```

Output files are saved to the `output_dir` shown in the response.

### Batch OCR

```
POST /ocr/batch
```

Process all images in a server folder:

```bash
curl -X POST "http://localhost:8111/ocr/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "${OCR_INPUT_BASE}/hindi",
    "lang": "hi",
    "save_annotated": true,
    "recursive": false
  }'
```

**Parameters** (JSON body):

| Name | Type | Required | Description |
|---|---|---|---|
| `folder_path` | string | Yes | Absolute path to image folder on the server |
| `lang` | string | Yes | Language code: `hi`, `mr`, `te`, `ta` |
| `save_annotated` | bool | No | Save annotated images (default: `true`) |
| `recursive` | bool | No | Include subfolders (default: `false`) |

**Response** (JSON):

```json
{
  "success": true,
  "folder_path": "${OCR_INPUT_BASE}/hindi",
  "language": "hi",
  "output_dir": "${OCR_OUTPUT_BASE}/batch/hi/20260215_143500_folder",
  "total_images": 25,
  "processed": 23,
  "failed": 2,
  "processing_time_seconds": 58.12,
  "results": [...]
}
```

---

## Output Structure

All outputs are saved under `${OCR_OUTPUT_BASE}` (configured in `.env`):

```
${OCR_OUTPUT_BASE}/
├── single/                         # Single-image results
│   └── hi/                         # By language
│       └── 20260215_143022_doc1/
│           ├── result.json         # Full OCR results
│           ├── extracted_text.txt  # Plain text
│           └── annotated.png       # Image with bounding boxes
└── batch/                          # Batch results
    └── hi/
        └── 20260215_143500_folder_name/
            ├── batch_summary.json
            ├── page_001/
            │   ├── result.json
            │   ├── extracted_text.txt
            │   └── annotated.png
            └── ...
```

---

## Supported Languages

| Language | Code | Script | Recognition Model |
|---|---|---|---|
| Hindi | `hi` | Devanagari | `devanagari_PP-OCRv5_mobile_rec` |
| Marathi | `mr` | Devanagari | `devanagari_PP-OCRv5_mobile_rec` |
| Telugu | `te` | Telugu | `te_PP-OCRv5_mobile_rec` |
| Tamil | `ta` | Tamil | `ta_PP-OCRv5_mobile_rec` |

All languages use `PP-OCRv5_server_det` for text detection (optimized for handwritten text accuracy).

---

## Configuration

### Environment Setup

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and update the paths for your machine:
   - `HOME_DIR`: Base path to your workspace
   - `OCR_OUTPUT_BASE`: Where OCR results will be saved
   - `OCR_INPUT_BASE`: Where input images are located

Environment variables (set in `.env` or pass to Docker):

| Variable | Default | Description |
|---|---|---|
| `HOME_DIR` | `/path/to/your/workspace` | Base directory for your setup |
| `OCR_OUTPUT_BASE` | `${HOME_DIR}/outputs/ocr` | Base output directory |
| `OCR_INPUT_BASE` | `${HOME_DIR}/resources/ocr_inputs` | Base input directory |
| `OCR_HOST` | `0.0.0.0` | Server bind host |
| `OCR_PORT` | `8111` | Server bind port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PRELOAD_LANGUAGES` | `` | Languages to preload on startup (comma-separated) |
| `MAX_IMAGE_SIZE_MB` | `50` | Max upload file size |

---

## Project Structure

```
indicOCR/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings and constants
│   ├── routes/
│   │   ├── ocr.py           # Single-image endpoint
│   │   ├── batch.py         # Batch endpoint
│   │   └── health.py        # Health + languages endpoints
│   ├── services/
│   │   ├── ocr_engine.py    # PaddleOCR wrapper (lazy singleton)
│   │   └── file_handler.py  # Output file management
│   ├── models/
│   │   ├── requests.py      # Pydantic request schemas
│   │   └── responses.py     # Pydantic response schemas
│   └── utils/
│       ├── image_utils.py   # Image validation
│       └── logging_config.py
├── tests/
├── .env.example             # Environment configuration template
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
└── README.md
```

---

## Development

```bash
# Run tests
pytest tests/ -v

# Run with auto-reload
uvicorn app.main:app --reload --port 8111

# Format code
black app/ tests/
isort app/ tests/
```

---

## License

Internal project — not for redistribution.
