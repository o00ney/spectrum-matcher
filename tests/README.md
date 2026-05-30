# Spectrum Matcher — Tests

## Test data

| File | Description |
|------|-------------|
| `b1_sample/` | Full Bruker 1H-NMR spectrum (B1 formulated flavor, MeOD solvent, 600 MHz) |
| `b1_sample.zip` | Pre-packaged zip of `b1_sample/` (759 KB) for drag-and-drop testing |

## Automated test suite

```bash
# Install test dependencies
pip install pytest pytest-qt

# Run all tests
PYTHONPATH="client:server:tests" pytest tests/ -v

# Run specific test files
PYTHONPATH="client:server:tests" pytest tests/test_api.py -v
PYTHONPATH="client:server:tests" pytest tests/test_downsample.py -v
PYTHONPATH="client:server:tests" pytest tests/test_export.py -v
```

## Test files

| File | Tests | Description |
|------|-------|-------------|
| `conftest.py` | — | Shared fixtures: mock server, api client, temp dirs |
| `test_downsample.py` | 9 | Uniform stride-based spectrum downsampling |
| `test_api.py` | 15 | API client: connection check, upload, response validation, cancel |
| `test_export.py` | 8 | CSV / JSON / PNG export utilities |

## What each test covers

### test_downsample.py
- Exact target, small arrays, typical 32,724→3,000 NMR reduction
- First/last element preservation, empty/single-element arrays
- NumPy array compatibility, output type is `list`

### test_api.py
- `ApiError` exception chaining
- `SpectrumMatcherApi` construction, URL stripping, timeout config
- Connection check (reachable + unreachable)
- Upload to mock server: response structure, result format
- Downsampled data: query_ppm/fid length, ppm_ds top-3 only
- Model info, base64 PNG validity, cancel flag behavior

### test_export.py
- CSV: basic export, empty results, missing fields
- JSON: basic export, pretty-printing, Unicode support
- Plot: figure save via Agg backend, export function delegation

## Manual verification

### Client GUI test
1. Start mock server: `python client/tools/mock_server.py`
2. Launch client: `cd client && python -m spectrum_matcher_client`
3. Verify UI: menu bar, status bar, tooltips, toolbar
4. Upload any folder/zip — verify results table, interactive plot
5. Test export: Ctrl+E (CSV), Ctrl+Shift+E (JSON), Ctrl+P (PNG)
6. Test history: upload multiple times, use combo to switch
7. Test shortcuts: Ctrl+O, Ctrl+Q, View > Plot Toolbar toggle

### API test via curl
```bash
# Mock server
curl -X POST http://127.0.0.1:8000/api/upload -F "file=@tests/b1_sample.zip"

# Production (real model)
curl --compressed -X POST https://nmr.ooney.xyz/api/upload \
  -F "file=@tests/b1_sample.zip" -o response.json
```

### Expected production results for B1
| Rank | Flavor | Probability |
|------|--------|-------------|
| 1 | Roman Chamomile Extraction-A | ~99.0% |
| 2 | Fig Extraction | ~92.4% |
| 3 | Chicory Extraction | ~86.4% |
