FROM python:3.10-slim

# System dependencies for OpenCV, PaddlePaddle, and GLib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libssl3 \
    ca-certificates \
    libgoogle-perftools4 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Suppress verbose PaddleX model source check during startup
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

# Use tcmalloc for better memory allocation performance with PaddlePaddle
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4
ENV OCR_OUTPUT_BASE=/app/outputs/ocr

EXPOSE 8111

# Create output directories at runtime using environment variable
RUN mkdir -p "${OCR_OUTPUT_BASE}/single" "${OCR_OUTPUT_BASE}/batch"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8111"]
