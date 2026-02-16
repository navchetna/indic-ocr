# IndicOCR Frontend

A modern, professional React + Vite application for optical character recognition (OCR) in Indic languages.

## Overview

**IndicOCR** provides an intuitive interface for extracting text from images in Hindi, Marathi, Telugu, Tamil, and Malayalam. Simply upload an image, select a language, and receive results with extracted text, confidence scores, and an annotated visualization of detected regions.

### Demo

![IndicOCR Demo](assets/indicOCR-Demo2.gif)

## Features

- 📸 **Drag-and-drop image upload** — intuitive file handling with preview
- 🌐 **Multi-language support** — Hindi, Marathi, Telugu, Tamil, Malayalam
- 📊 **Detailed results** — extracted text, per-region confidence scores, annotated images
- 🗂️ **Task history** — organized by language, expandable sections for easy navigation
- 🎨 **Professional design** — clean UI with teal accents, rounded containers, borders
- 🔄 **Real-time feedback** — processing indicators and error handling
- 📦 **Responsive layout** — works seamlessly on desktop and tablet

## Development

### Setup

```bash
cd frontend
npm install
npm run dev
```

The app runs on `http://localhost:3000` by default, with API proxy to the backend at `http://localhost:8111`.

### Build

```bash
npm run build
```

Outputs optimized assets to `dist/`.

## Docker Deployment

```bash
docker compose up --build -d indicocr-ui
```

The frontend container runs on port **8112** and proxies API requests to the backend service (`indicocr:8111`). Output files are served from the mounted `/outputs/ocr/` directory.

## Architecture

- **Framework**: React 18 + Vite 6
- **HTTP Client**: Fetch API with custom `ocr.js` service layer
- **Styling**: Plain CSS with design tokens (variables)
- **Server**: nginx with SPA fallback and API proxy
- **Container**: Multi-stage Docker build (Node → nginx)

## API Integration

The frontend communicates with the IndicOCR backend:

- `POST /ocr/single` — submit single image for OCR
- `GET /ocr/languages` — fetch supported languages
- `GET /outputs/*` — browse results (autoindexed JSON from nginx)

## Theme

- **Palette**: Teal (primary), grays (neutral), greyish-red (alerts)
- **Style**: Rounded corners (12px), subtle borders (1px), soft shadows
- **Typography**: Inter font family, responsive sizing

## Directory Structure

```
frontend/
├── index.html                 # SPA entry point
├── vite.config.js            # Build config
├── nginx.conf                # Reverse proxy & SPA fallback
├── Dockerfile                # Multi-stage build
├── package.json              # Dependencies
├── src/
│   ├── main.jsx              # React root
│   ├── App.jsx               # Main app component
│   ├── index.css             # Global styles & design tokens
│   ├── api/
│   │   └── ocr.js            # API service layer
│   └── components/
│       ├── Header.jsx        # Navigation header
│       ├── Sidebar.jsx       # Task history & mode toggle
│       ├── UploadForm.jsx    # Image upload interface
│       └── ResultView.jsx    # OCR results display
└── public/
    └── favicon.svg           # App icon
```

## License

Part of the IndicOCR project.
