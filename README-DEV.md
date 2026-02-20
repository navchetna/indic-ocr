# IndicOCR — Developer Reference

> **Platform:** Intel Xeon 6 processors, CPU-based inference only.

---

## 1. Quick Start (Development)

### Local

```bash
cd indicOCR
cp .env.example .env          # edit HOME_DIR, OCR_OUTPUT_BASE, OCR_INPUT_BASE
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8111 --reload
```

### Docker

```bash
cd indicOCR
cp .env.example .env          # edit paths
docker compose up --build -d
docker compose logs -f indicocr
```

| Container | Port | Description |
|---|---|---|
| `indicocr` | 8111 | FastAPI backend |
| `indicocr-ui` | 8112 | Nginx frontend |

---

## 2. Project Structure

```
indicOCR/
├── app/
│   ├── main.py                  # FastAPI entry, lifespan, CORS
│   ├── config.py                # Settings from env vars + .env
│   ├── routes/
│   │   ├── ocr.py               # POST /ocr/single
│   │   ├── batch.py             # POST /ocr/batch
│   │   └── health.py            # GET /health, GET /ocr/languages
│   ├── services/
│   │   ├── ocr_engine.py        # PaddleOCR wrapper, image preprocessing
│   │   └── file_handler.py      # Output directory & file I/O
│   ├── models/
│   │   ├── requests.py          # Pydantic request schemas
│   │   └── responses.py         # Pydantic response schemas
│   └── utils/
│       ├── image_utils.py       # Image validation
│       └── logging_config.py    # Logging setup
├── benchmarks/
│   ├── benchmark.py             # CLI benchmarking tool
│   └── README.md                # Benchmark documentation
├── frontend/                    # Nginx + static UI
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
└── .env.example
```

---

## 3. OCR Engine Internals

### 3.1 PaddleOCR Pipeline

```
Input Image
    │
    ▼
[Preprocessing] — resize if longest side > 960px (see §3.2)
    │
    ▼
1. Text Detection (PP-OCRv5_server_det)
    │   → bounding box polygons around text regions
    ▼
2. Crop & sort regions (top-to-bottom, left-to-right)
    │
    ▼
3. Text Recognition (language-specific model)
    │   → (text, confidence) per region
    ▼
Output: list of { text, confidence, bounding_box }
```

### 3.2 Image Preprocessing — Automatic Resize

**Location:** `app/services/ocr_engine.py` → `_preprocess_image()`

Images with a longest side exceeding `MAX_LONG_SIDE` (default **960 px**) are
automatically resized before being sent to PaddleOCR.

#### Why 960 px? — Model Config Evidence

The value 960 is **not arbitrary** — it comes directly from the model's own
inference configuration files (stored at `/root/.paddlex/official_models/`
inside the container).

**Detection model (`PP-OCRv5_server_det/inference.yml`):**

```yaml
PreProcess:
  transform_ops:
    - DetResizeForTest:
        resize_long: 960          # ← PaddleOCR resizes to 960 internally
```

This means PaddleOCR's own preprocessing resizes the input image's longest
side to **960 px** before feeding it to the detection network. Any pixels
above 960 are discarded by the model anyway.

The TensorRT dynamic shape config confirms the operating range:

```yaml
trt_dynamic_shapes:
  x:
    - [1, 3,   32,   32]    # minimum
    - [1, 3,  736,  736]    # optimal
    - [1, 3, 4000, 4000]    # maximum
```

The model accepts up to 4000×4000 but is optimized for **736–960 px**.

**Recognition model (`devanagari_PP-OCRv5_mobile_rec/inference.yml`):**

```yaml
PreProcess:
  transform_ops:
    - RecResizeImg:
        image_shape: [3, 48, 320]   # ← fixed 48×320 per cropped region
```

Each detected text region is cropped and resized to a fixed **48×320 px**
before recognition. This is independent of the input image resolution —
only the detection stage is affected by overall image size.

**Both configs are the same across all languages** — detection uses a shared
model (`PP-OCRv5_server_det`), and all recognition models use 48×320 crops.

#### Why dimension-based, not file-size-based

File size is a poor proxy for inference cost. A 400 KB PNG can have higher
resolution than a 600 KB JPEG due to compression differences. CPU inference
time scales with **pixel count**, so the longest-side check directly targets
the cost driver.

#### Performance impact (Intel Xeon 6, CPU)

| Image | Resolution | Inference Time | Regions Detected |
|---|---|---|---|
| Screenshot (188 KB) | ~1200×800 | **3.0 s** | 26 |
| Downloaded scan (1.4 MB) | 3456×4608 | **139 s** | 15 |
| Same scan, pre-resized to 960 | ~720×960 | **~3-5 s** | ~25+ |

Key findings:
- **46× slower** on the full-res image without pre-resize
- **Fewer regions detected** at high resolution — the detection model's
  receptive field is tuned for ~960 px; oversized images cause text regions
  to fragment or fall below detection thresholds
- Pre-resizing to 960 px restores both speed and accuracy

#### Implementation

```python
MAX_LONG_SIDE: int = 960

def _preprocess_image(image_path: str | Path) -> str:
    img = Image.open(image_path)
    w, h = img.size
    long_side = max(w, h)

    if long_side <= MAX_LONG_SIDE:
        return str(image_path)          # no-op for small images

    scale = MAX_LONG_SIDE / long_side
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(image_path).suffix)
    img.save(tmp.name, quality=95)
    return tmp.name                     # resized temp path
```

Both `run_ocr()` and `run_ocr_and_save_annotated()` call `_preprocess_image()`
before passing the image to `engine.predict()`.

### 3.3 PP-OCRv5 Result Parsing

PaddleOCR PP-OCRv5 returns `OCRResult` objects that are **dict-like**, not
plain attribute containers. The actual OCR data lives inside:

```python
prediction.json["res"]
# Contains: rec_texts, rec_scores, dt_polys
```

**Not** as direct attributes (`prediction.rec_texts` silently returns `{}`).
This was a breaking change from older PaddleOCR versions.

### 3.4 Lazy Singleton Pattern

One `PaddleOCR` engine instance per language, created on first request:

```python
class OCREngineManager:
    _engines: dict[str, PaddleOCR] = {}

    @classmethod
    def get_engine(cls, lang: str) -> PaddleOCR:
        if lang not in cls._engines:
            cls._engines[lang] = PaddleOCR(lang=lang, ...)
        return cls._engines[lang]
```

First request per language takes ~5–6 s (model download + load). Subsequent
requests reuse the cached engine.

### 3.5 Models Used

| Component | Model | Notes |
|---|---|---|
| Detection | `PP-OCRv5_server_det` | Shared across all languages; better on handwritten text |
| Recognition (hi/mr) | `devanagari_PP-OCRv5_mobile_rec` | Shared Devanagari model |
| Recognition (te) | `te_PP-OCRv5_mobile_rec` | Telugu-specific |
| Recognition (ta) | `ta_PP-OCRv5_mobile_rec` | Tamil-specific |

Models are downloaded from HuggingFace on first use and cached at
`/root/.paddlex/official_models/` inside the container.

### 3.6 Memory Allocator — tcmalloc

The Dockerfile sets `LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4`
to use Google's tcmalloc instead of glibc's default malloc. This reduces
memory fragmentation and allocation overhead during repeated inference
cycles, which is beneficial for long-running PaddlePaddle services.

---

## 4. API Endpoints

### POST `/ocr/single`

Upload a single image for OCR.

```bash
curl -X POST "http://localhost:8111/ocr/single?lang=hi&save_annotated=false" \
  -F "file=@image.jpg"
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file` | multipart | Yes | Image file (PNG, JPG, TIFF, BMP, WEBP) |
| `lang` | query | Yes | Language code: `hi`, `mr`, `te`, `ta` |
| `save_annotated` | query | No | Save annotated image (default: `true`) |

### POST `/ocr/batch`

Process all images in a server-side folder.

```bash
curl -X POST "http://localhost:8111/ocr/batch" \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/user-ali/resources/ocr_inputs/hindi", "lang": "hi"}'
```

### GET `/health`

Health check — returns loaded languages and service status.

### GET `/ocr/languages`

List supported languages, codes, and scripts.

---

## 5. Benchmarking

Full documentation: [`benchmarks/README.md`](benchmarks/README.md)

### Quick run

```bash
cd indicOCR/benchmarks
python -m benchmark -n 10 -l hi       # 10 Hindi images
python -m benchmark -n 5 -l hi,te     # 5 each, Hindi + Telugu
```

### Output

Two CSVs per run in `/user-ali/outputs/ocr/benchmarks/`:

| File | Contents |
|---|---|
| `benchmark_<run_id>_details.csv` | Per-image: latency, confidence, accuracy, ground truth text, extracted text |
| `benchmark_<run_id>_summary.csv` | Per-language aggregates: mean/median/p95 latency, mean accuracy |

### Key CLI flags

| Flag | Default | Description |
|---|---|---|
| `-n` | `100` | Images per language |
| `-l` | `hi,te` | Languages (comma-separated) |
| `-u` | `default` | User tag in run ID |
| `--api-url` | `http://localhost:8111` | API base URL |
| `--seed` | `42` | Reproducible sampling |

### Accuracy metric

**CER (Character Error Rate)** via `rapidfuzz.distance.Indel`.
Accuracy = `1 - CER`. Both OCR output and ground truth are normalized to
single-line format before comparison.

---

## 6. Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOME_DIR` | — (required) | Base path for the workspace |
| `OCR_OUTPUT_BASE` | `${HOME_DIR}/outputs/ocr` | All OCR outputs saved here |
| `OCR_INPUT_BASE` | `${HOME_DIR}/resources/ocr_inputs` | Default input folder |
| `OCR_HOST` | `0.0.0.0` | Bind address |
| `OCR_PORT` | `8111` | Bind port |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `PRELOAD_LANGUAGES` | `` (empty) | Comma-separated langs to load on startup |
| `MAX_IMAGE_SIZE_MB` | `50` | Max upload size |

### Tunable Constants in `ocr_engine.py`

| Constant | Default | Source | Description |
|---|---|---|---|
| `MAX_LONG_SIDE` | `960` | `PP-OCRv5_server_det/inference.yml` → `DetResizeForTest.resize_long` | Pre-resize threshold matching the model's native input size |

---

## 7. Docker

### Build & Run

```bash
docker compose up --build -d
docker compose logs -f indicocr       # backend logs
docker compose logs -f indicocr-ui    # frontend logs
docker compose down                   # stop
```

### Volumes

| Host Path | Container Path | Purpose |
|---|---|---|
| `${OCR_OUTPUT_BASE}` | `${OCR_OUTPUT_BASE}` | OCR results (read/write) |
| `${OCR_INPUT_BASE}` | `${OCR_INPUT_BASE}` | Input images for batch mode |

### Dockerfile

- Base: `python:3.10-slim`
- System deps: `libgl1`, `libglib2.0-0`, `libgomp1`, `libgoogle-perftools4` (tcmalloc)
- Env: `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`, `LD_PRELOAD=libtcmalloc.so.4`
- Exposes port `8111`
- Entry: `uvicorn app.main:app --host 0.0.0.0 --port 8111`

---

## 8. Dependencies

```
fastapi>=0.115.0          # Web framework
uvicorn[standard]>=0.30.0 # ASGI server
paddleocr>=3.0.0          # OCR engine
paddlepaddle>=3.0.0       # Deep learning framework (CPU)
Pillow>=10.0.0            # Image preprocessing & resize
opencv-python-headless    # Image I/O
pydantic>=2.0.0           # Data validation
pydantic-settings>=2.0.0  # Env-based config
aiofiles>=24.0.0          # Async file I/O
rapidfuzz>=3.0.0          # CER computation (benchmarks)
requests>=2.31.0          # HTTP client (benchmarks)
```

---

## 9. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Pre-resize to 960 px** | Matches `DetResizeForTest.resize_long: 960` from the model config. Input above 960 px is discarded by PaddleOCR internally, so pre-resizing avoids wasting memory/CPU on pixels that get thrown away. |
| **Dimension-based resize, not file-size** | File size depends on format/compression; pixel count is the actual cost driver. |
| **tcmalloc via LD_PRELOAD** | PaddlePaddle does many small tensor allocations; tcmalloc's thread-local caches reduce fragmentation and allocation overhead. |
| **PP-OCRv5_server_det for detection** | Higher accuracy on handwritten text vs the mobile variant. |
| **Lazy model loading** | Avoids 20+ second startup loading all 4 language models. |
| **Parse `prediction.json['res']`** | PP-OCRv5 `OCRResult` is dict-like; data is nested in `.json['res']`, not exposed as top-level attributes. |
| **`asyncio.to_thread` for OCR calls** | PaddleOCR is CPU-bound; running in a thread keeps FastAPI responsive. |
| **Two benchmark CSVs** | Details CSV has per-image metrics + full text; summary CSV has per-language aggregates. |
| **LANCZOS resize at quality=95** | Best downscale quality; near-lossless JPEG saves for temp files. |

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `regions=0` on all images | Parsing `prediction.rec_texts` directly (old API) | Use `prediction.json['res']['rec_texts']` instead |
| 120+ second latency per image | Image resolution too high (3000+ px) | `MAX_LONG_SIDE=960` auto-resize handles this; verify preprocessing is active in logs |
| `Resized image size exceeds max_side_limit` in logs | PaddleOCR's internal 4000 px limit being hit | Our 960 px pre-resize prevents this from being reached |
| `Read timed out` in benchmark | API timeout too short | Benchmark uses 600s timeout; increase if needed |
| Model download on first request | Normal — HuggingFace download on first use per language | Set `PRELOAD_LANGUAGES=hi,te` to load at startup |
| High memory usage | Each language engine ~500 MB–1 GB | Load only needed languages; don't preload all 4 |
