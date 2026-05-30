# NMR Spectrum Matcher

Deep learning based NMR spectrum matching tool. Upload a Bruker 1H-NMR
spectrum to identify plant flavor components via the DeepMID model
(Siamese CNN + Spatial Pyramid Pooling, 470K parameters).

## Download (Windows)

Download the latest `.exe` from [Releases](https://github.com/o00ney/spectrum-matcher/releases).
Unzip and run `NMR-Spectrum-Matcher.exe` — no Python installation required.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Client (PySide6 + matplotlib)                          │
│  • Interactive NMR spectrum comparison plot             │
│  • Results table with sort / export / history           │
│  • Drag & drop Bruker .zip or folder                    │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTPS (gzip compressed)
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Server (FastAPI + TensorFlow)                          │
│  • DeepMID model inference (GPU accelerated)            │
│  • Bruker format reading + airPLS baseline correction   │
│  • Downsampled spectrum data for client-side rendering  │
└─────────────────────────────────────────────────────────┘
```

## Setup

### Client (from source)

```bash
cd client
pip install PySide6 requests matplotlib
python -m spectrum_matcher_client
```

Default server: `https://nmr.ooney.xyz`. Change in UI or via
`SPECTRUM_MATCHER_SERVER_URL` environment variable.

### Server

```bash
cd server
pip install fastapi uvicorn matplotlib tensorflow nmrglue
uvicorn main:app --host 0.0.0.0 --port 8000
```

Requires model file at `server/model/model_1/test_nmr.h5` and reference
data at `server/data/plant_flavors/`. Falls back to mock mode if absent.

### Mock Server (for client testing)

```bash
python client/tools/mock_server.py
# Client connects to http://127.0.0.1:8000
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload Bruker spectrum .zip, get results + plot |
| GET | `/docs` | FastAPI docs (health check) |

## Tests

```bash
pip install pytest pytest-qt
PYTHONPATH="client:server:tests" pytest tests/ -v
```

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `SPECTRUM_MATCHER_SERVER_URL` | `https://nmr.ooney.xyz` | Client server URL |
| `SPECTRUM_MATCHER_TIMEOUT` | `120` | Request timeout (seconds) |
| `SPECTRUM_MATCHER_MODEL` | `model/model_1/test_nmr` | Model file path |
| `SPECTRUM_MATCHER_DATA` | `data/plant_flavors` | Reference data path |
