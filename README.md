# TRMNL Local Server

A private backend for TRMNL e-ink displays that manages image carousels and renders dynamic content, such as curated poetry, into device-ready BMP files.

## Quick Start

The server requires Python 3.12 or higher and Playwright for image rendering.

```bash
# Install dependencies and the package
pip install .

# Install the browser engine for image rendering
playwright install chromium

# Launch the server
trmnl
```

The server runs by default on `http://0.0.0.0:8070`.

## Core Functionality: The Poem Engine

The primary feature of this implementation is the Poem Engine, which automates the delivery of formatted literature to an e-ink display:

1.  **Data Retrieval**: Pulls from the Poetry Foundation dataset (via KaggleHub).
2.  **LLM Restoration**: Uses an LLM to forensicially reconstruct canonical line breaks and stanza structures if the source text is "flattened" prose.
3.  **BWR Rendering**: Converts processed text into an 800x480 1-bit BMP optimized for e-ink contrast using Playwright.
4.  **Carousel Management**: Rotates images according to the device refresh interval.

## Architecture

The project consists of three main layers:

### API Layer (`app.py`)
Implements the private TRMNL protocol to communicate directly with the device:
- `GET /api/setup`: Handles initial device registration.
- `GET /api/display`: Provides the device with the next image metadata and refresh rates.
- `GET /api/image/{filename}`: Serves the generated 1-bit BMP files.

### Management Layer (`carousel.py`)
Handles the "working directory" logic for the device. It ensures that only one active image is prepared at a time, manages unique filenames to prevent device caching issues, and coordinates with content engines.

### Engine Layer (`engines/`)
Pluggable modules that provide the `ImageEngine` protocol. The included `PoemEngine` demonstrates:
- HTML-to-BMP conversion via `generate.py`.
- Automated text cleaning and restoration using Jinja2 templates for LLM prompting.
- Local caching of generated images to minimize compute overhead.

## Installation and Setup

### Prerequisites
- **Hostname Requirement**: By default, the application checks for a specific host environment (`caruana`). This check is located in `src/trmnl/__init__.py`.
- **Dataset**: To use the Poem Engine, download the required dataset:
  ```python
  import kagglehub
  kagglehub.dataset_download("tgdivy/poetry-foundation-poems")
  ```

### Configuration
Settings are managed in `config.py` and utilize XDG base directories for caching. Key parameters include:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `refresh_interval` | 60 | Device poll rate in seconds |
| `server_ip` | 10.0.0.82 | IP address the device targets |
| `port` | 8070 | Server port |
| `CACHE_DIR` | `~/.cache/trmnl` | Location for generated BMPs |

## Basic Usage

### Running Content Processes
For the Poem Engine, a background process can be used to pre-render images and avoid latency during device polling:

```bash
python src/trmnl/engines/poems/background_process.py
```

### Image Conversion
To manually convert existing images to the TRMNL-compatible 1-bit BMP format:

```python
from trmnl.images.convert_image import image_to_bmp
image_to_bmp("source_photo.png", "output.bmp")
```

### Deployment
The server uses Uvicorn. For production-style logs and persistent operation, use the provided entry point:

```bash
trmnl
```

## Hardware Compatibility
This server is designed for 800x480 monochrome displays. Images are automatically converted to 1-bit (black and white) using Floyd–Steinberg dithering via Pillow to ensure maximum clarity on e-ink hardware.
