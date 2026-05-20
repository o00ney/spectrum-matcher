# NMR Spectrum Matcher

Deep learning based NMR spectrum matching tool. Upload a Bruker NMR spectrum
and identify plant flavor components via the DeepMID model.

## Architecture

```
Qt Client (PySide6)  ──HTTP──▶  FastAPI Server  ──▶  DeepMID Model
  spectrum-matcher/               spectrum-matcher/
  client/main.py                  server/main.py
                                  server/model_runner.py
                                  server/plotter.py
```

## Setup

### Server

```bash
cd server
pip install -r ../requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Client

```bash
cd client
pip install PySide6 requests
python main.py
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/upload | Upload Bruker spectrum zip |
| GET | /api/plot/{id} | Retrieve comparison plot |

## Model Integration

When the DeepMID model is ready, implement the `TODO` sections in
`server/model_runner.py`:

1. `init()` — load model weights, preprocess reference library
2. `match()` — preprocess query spectrum, run prediction, return sorted results

See `server/model_runner.py` for the detailed interface contract.
