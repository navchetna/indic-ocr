# IndicOCR — Project Plan

> **Platform:** This project is specifically designed to run on **Intel Xeon 6** processors with CPU-based inference.

## 1. Overview

**IndicOCR** is a FastAPI-based OCR service for extracting text from document images of handwritten Indic-language texts. It leverages **PaddleOCR (PP-OCRv5)** as the backend processing engine with language-specific recognition models for Hindi, Marathi, Telugu, and Tamil.

The service exposes REST endpoints for **single-image** and **batch (folder-based)** processing, supporting language-agnostic invocation where the target language is passed as a request parameter.

---

## 2. Tech Stack

| Layer | Technology | Version / Notes |
|---|---|---|
| **Language** | Python | 3.10+ |
| **Web Framework** | FastAPI | 0.115+ with Uvicorn ASGI server |
| **OCR Engine** | PaddleOCR | PP-OCRv5 (via `paddleocr` Python package) |
| **Deep Learning** | PaddlePaddle | CPU (`paddlepaddle` package) |
| **Image Processing** | OpenCV, Pillow | For image I/O and annotated output |
| **Serialization** | Pydantic v2 | Request/response models |
| **Async File I/O** | aiofiles | Non-blocking file writes |
| **Containerization** | Docker + Docker Compose | Multi-stage build |
| **Logging** | Python `logging` | Structured JSON logging |
| **Testing** | pytest + httpx | Async test client |

---

## 3. Supported Languages

| Language | ISO Code | Script | PaddleOCR Recognition Model | Dictionary |
|---|---|---|---|---|
| Hindi | `hi` | Devanagari | `devanagari_PP-OCRv5_mobile_rec` | `ppocrv5_devanagari_dict.txt` |
| Marathi | `mr` | Devanagari | `devanagari_PP-OCRv5_mobile_rec` | `ppocrv5_devanagari_dict.txt` |
| Telugu | `te` | Telugu | `te_PP-OCRv5_mobile_rec` | `ppocrv5_te_dict.txt` |
| Tamil | `ta` | Tamil | `ta_PP-OCRv5_mobile_rec` | `ppocrv5_ta_dict.txt` |

> **Note:** Hindi and Marathi share the Devanagari recognition model. Telugu and Tamil each have dedicated models. Detection uses the universal `PP-OCRv5_server_det` model for all languages (better accuracy on handwritten text).

---

## 4. PaddleOCR Processing Pipeline

```
Input Image
    │
    ├── [Optional] Document Orientation Classification (0°/90°/180°/270°)
    ├── [Optional] Document Unwarping (flatten curved/warped pages)
    │
    ▼
1. Text Detection (PP-OCRv5_server_det)
    │   → Produces bounding box polygons around text regions
    ▼
2. Crop & Sort detected text regions (top-to-bottom, left-to-right)
    │
    ├── [Optional] Textline Orientation Classification (handle rotated lines)
    │
    ▼
3. Text Recognition (language-specific model)
    │   → Produces (text, confidence_score) per detected region
    ▼
Output: List of { bounding_box, text, confidence }
```

### Key PaddleOCR API Usage

```python
from paddleocr import PaddleOCR

# Initialize with language and server detection model
ocr = PaddleOCR(
    lang='hi',                              # Language code
    use_doc_orientation_classify=False,      # Disable for speed (enable if needed)
    use_doc_unwarping=False,                 # Disable for speed
    use_textline_orientation=False,          # Disable for speed
    text_detection_model_name="PP-OCRv5_server_det",  # Server model for accuracy
)

# Run inference
result = ocr.predict("path/to/image.png")

# Each result contains:
# - rec_texts: list of recognized text strings
# - rec_scores: list of confidence scores
# - dt_polys: list of bounding box polygons
# - save_to_img("output_dir")  → Annotated image
# - save_to_json("output_dir") → JSON result
```

---

## 5. Application Architecture

```
indicOCR/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point, lifespan, CORS
│   ├── config.py                # Settings (paths, model config, defaults)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── ocr.py               # Single-image OCR endpoint
│   │   ├── batch.py             # Batch (folder) OCR endpoint
│   │   └── health.py            # Health check endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_engine.py        # PaddleOCR engine wrapper (singleton per lang)
│   │   └── file_handler.py      # File I/O, output directory management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py          # Pydantic request models
│   │   └── responses.py         # Pydantic response models
│   └── utils/
│       ├── __init__.py
│       ├── image_utils.py       # Image validation, format conversion
│       └── logging_config.py    # Logging setup
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Fixtures (test client, sample images)
│   ├── test_ocr.py              # Single-image endpoint tests
│   └── test_batch.py            # Batch endpoint tests
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── PROJECT_PLAN.md              # This file
├── README.md                    # Project README
└── .env.example                 # Environment variables template
```

---

## 6. API Endpoints

### 6.1 Health Check

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health and loaded model info |

**Response:**
```json
{
  "status": "healthy",
  "loaded_languages": ["hi", "mr", "te", "ta"],
  "detection_model": "PP-OCRv5_server_det",
  "version": "1.0.0"
}
```

---

### 6.2 Single Image OCR

| Method | Path | Description |
|---|---|---|
| `POST` | `/ocr/single` | Process a single uploaded image |

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | `UploadFile` | Yes | Image file (PNG, JPG, JPEG, TIFF, BMP, WEBP) |
| `lang` | `str` (query) | Yes | Language code: `hi`, `mr`, `te`, `ta` |
| `save_annotated` | `bool` (query) | No | Save annotated image (default: `true`) |

**Response:**
```json
{
  "success": true,
  "filename": "document_001.png",
  "language": "hi",
  "output_dir": "/user-ali/outputs/ocr/single/hi/20260215_143022_document_001",
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

**Output Files (saved to disk):**
```
/user-ali/outputs/ocr/single/hi/20260215_143022_document_001/
├── result.json           # Structured OCR results
├── extracted_text.txt    # Plain text output
└── annotated.png         # Image with bounding boxes drawn
```

---

### 6.3 Batch OCR (Server Folder)

| Method | Path | Description |
|---|---|---|
| `POST` | `/ocr/batch` | Process all images in a server folder |

**Request:** `application/json`

```json
{
  "folder_path": "/user-ali/resources/ocr_inputs/hindi/Page_Level_Training_Set",
  "lang": "hi",
  "save_annotated": true,
  "recursive": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `folder_path` | `str` | Yes | Absolute path to folder containing images on the server |
| `lang` | `str` | Yes | Language code: `hi`, `mr`, `te`, `ta` |
| `save_annotated` | `bool` | No | Save annotated images (default: `true`) |
| `recursive` | `bool` | No | Scan subfolders recursively (default: `false`) |

**Response:**
```json
{
  "success": true,
  "folder_path": "/user-ali/resources/ocr_inputs/hindi/Page_Level_Training_Set",
  "language": "hi",
  "output_dir": "/user-ali/outputs/ocr/batch/hi/20260215_143500_Page_Level_Training_Set",
  "total_images": 25,
  "processed": 23,
  "failed": 2,
  "processing_time_seconds": 58.12,
  "results": [
    {
      "filename": "page_001.png",
      "success": true,
      "results": [...],
      "full_text": "...",
      "processing_time_seconds": 2.1
    },
    {
      "filename": "corrupt_image.jpg",
      "success": false,
      "error": "Failed to decode image"
    }
  ]
}
```

**Output Files (saved to disk):**
```
/user-ali/outputs/ocr/batch/hi/20260215_143500_Page_Level_Training_Set/
├── batch_summary.json              # Aggregated results for all images
├── page_001/
│   ├── result.json
│   ├── extracted_text.txt
│   └── annotated.png
├── page_002/
│   ├── result.json
│   ├── extracted_text.txt
│   └── annotated.png
└── ...
```

---

### 6.4 Supported Languages

| Method | Path | Description |
|---|---|---|
| `GET` | `/ocr/languages` | List supported languages and their models |

**Response:**
```json
{
  "languages": [
    {"code": "hi", "name": "Hindi", "script": "Devanagari"},
    {"code": "mr", "name": "Marathi", "script": "Devanagari"},
    {"code": "te", "name": "Telugu", "script": "Telugu"},
    {"code": "ta", "name": "Tamil", "script": "Tamil"}
  ]
}
```

---

## 7. OCR Engine Design

### 7.1 Lazy Singleton Pattern

PaddleOCR models are large and take time to load. The engine uses a **lazy singleton per language** pattern:

```python
class OCREngineManager:
    _engines: dict[str, PaddleOCR] = {}

    @classmethod
    def get_engine(cls, lang: str) -> PaddleOCR:
        if lang not in cls._engines:
            cls._engines[lang] = PaddleOCR(
                lang=lang,
                text_detection_model_name="PP-OCRv5_server_det",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        return cls._engines[lang]
```

### 7.2 Model Loading Strategy

- Models are loaded **on first request** for a given language (lazy loading)
- Once loaded, the engine instance is cached for all subsequent requests
- Optionally, a `PRELOAD_LANGUAGES` config can trigger model loading on app startup

### 7.3 Resource Considerations

| Factor | Strategy |
|---|---|
| Memory | Each language engine ~500MB–1GB RAM; share detection model across languages |
| Concurrency | Use FastAPI's async with `run_in_executor` for CPU-bound OCR calls |
| Batch size | Process images sequentially within a batch to control memory |

---

## 8. Output Structure

All outputs are saved under `/user-ali/outputs/ocr/` with separation by mode:

```
/user-ali/outputs/ocr/
├── single/                    # Single-image results
│   ├── hi/                    # Grouped by language
│   │   ├── 20260215_143022_document_001/
│   │   │   ├── result.json
│   │   │   ├── extracted_text.txt
│   │   │   └── annotated.png
│   │   └── ...
│   ├── mr/
│   ├── te/
│   └── ta/
└── batch/                     # Batch results
    ├── hi/
    │   ├── 20260215_143500_Page_Level_Training_Set/
    │   │   ├── batch_summary.json
    │   │   ├── page_001/
    │   │   │   ├── result.json
    │   │   │   ├── extracted_text.txt
    │   │   │   └── annotated.png
    │   │   └── ...
    │   └── ...
    ├── mr/
    ├── te/
    └── ta/
```

---

## 9. Docker Configuration

### Dockerfile (Multi-stage)

- **Base:** `python:3.10-slim`
- **System deps:** `libgl1-mesa-glx`, `libglib2.0-0`, `libgomp1` (OpenCV runtime)
- **Python deps:** PaddlePaddle (CPU), PaddleOCR, FastAPI, uvicorn
- **Expose:** Port 8111
- **Volumes:** Mount `/user-ali/outputs/ocr` and input directories

### Docker Compose

```yaml
services:
  indicocr:
    build: .
    ports:
      - "8111:8111"
    volumes:
      - /user-ali/outputs/ocr:/user-ali/outputs/ocr
      - /user-ali/resources/ocr_inputs:/user-ali/resources/ocr_inputs
    environment:
      - OCR_OUTPUT_BASE=/user-ali/outputs/ocr
      - LOG_LEVEL=INFO
      - PRELOAD_LANGUAGES=hi,mr
```

---

## 10. Configuration & Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OCR_OUTPUT_BASE` | `/user-ali/outputs/ocr` | Base directory for all OCR outputs |
| `OCR_HOST` | `0.0.0.0` | FastAPI bind host |
| `OCR_PORT` | `8111` | FastAPI bind port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PRELOAD_LANGUAGES` | `` (empty) | Comma-separated lang codes to preload on startup |
| `MAX_IMAGE_SIZE_MB` | `50` | Maximum upload file size in MB |
| `SUPPORTED_EXTENSIONS` | `.png,.jpg,.jpeg,.tiff,.bmp,.webp` | Allowed image file extensions |

---

## 11. Error Handling

| Scenario | HTTP Code | Error Response |
|---|---|---|
| Unsupported language code | 400 | `{"detail": "Unsupported language 'xx'. Supported: hi, mr, te, ta"}` |
| Invalid image file | 400 | `{"detail": "Invalid image file. Supported formats: PNG, JPG, TIFF, BMP, WEBP"}` |
| Folder not found | 404 | `{"detail": "Folder not found: /path/to/folder"}` |
| No images in folder | 400 | `{"detail": "No supported image files found in folder"}` |
| File too large | 413 | `{"detail": "File size exceeds 50MB limit"}` |
| OCR engine error | 500 | `{"detail": "OCR processing failed: <error_message>"}` |

---

## 12. Development Roadmap

### Phase 1 — MVP (Current)
- [x] Project structure and configuration
- [x] PaddleOCR engine wrapper with lazy loading
- [x] Single-image OCR endpoint (`POST /ocr/single`)
- [x] Batch OCR endpoint (`POST /ocr/batch`)
- [x] Health check and language listing endpoints
- [x] JSON + plain text + annotated image output
- [x] Docker support
- [x] Project README and Project Plan

### Phase 2 — Enhancements
- [ ] Async batch processing with job status polling (`GET /ocr/batch/{job_id}/status`)
- [ ] WebSocket support for real-time batch progress
- [ ] Confidence threshold filtering (skip low-confidence results)
- [ ] Custom model configuration per request
- [ ] Rate limiting and API key authentication
- [ ] Prometheus metrics endpoint

### Phase 3 — Extended
- [ ] Additional Indic languages (Kannada, Bengali, Gujarati, Punjabi, etc.)
- [ ] Document structure analysis (tables, headers via PPStructureV3)
- [ ] PDF input support (render pages to images)
- [ ] Model fine-tuning pipeline for custom handwriting styles
- [ ] Horizontal scaling with task queue (Celery/Redis)

---

## 13. Testing Strategy

| Test Type | Tool | Scope |
|---|---|---|
| Unit | pytest | OCR engine wrapper, file handler, image validation |
| Integration | pytest + httpx AsyncClient | Endpoint request/response validation |
| E2E | curl / Postman | Full pipeline with real Indic handwriting images |
| Load | locust | Concurrency and throughput benchmarks |

### Sample Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# E2E: Single image
curl -X POST "http://localhost:8111/ocr/single?lang=hi" \
  -F "file=@/user-ali/resources/ocr_inputs/hindi/Page_Level_Training_Set/sample.png"

# E2E: Batch
curl -X POST "http://localhost:8111/ocr/batch" \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/user-ali/resources/ocr_inputs/hindi/Page_Level_Training_Set", "lang": "hi"}'
```

---

## 14. Key Design Decisions

| Decision | Rationale |
|---|---|
| **PP-OCRv5_server_det** for detection | Higher accuracy on handwritten text vs mobile variant |
| **Lazy model loading** | Avoid loading all 3 recognition models at startup; load on demand |
| **Sync OCR in thread pool** | PaddleOCR is CPU-bound; wrapping in `asyncio.to_thread()` keeps FastAPI responsive |
| **Separate single/batch dirs** | Clean output organization; prevents mixing one-off and bulk results |
| **Language as explicit param** | Language-agnostic endpoints; same API for all scripts |
| **No preprocessing flags** | Disable `doc_orientation_classify`, `doc_unwarping`, `textline_orientation` for speed; can be enabled later |
