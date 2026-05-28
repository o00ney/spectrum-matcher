# Test Cases

## B1 Formulated Flavor

`b1_sample/` is a real Bruker 1H-NMR spectrum of a formulated flavor (B1).

**Quick test:**
1. Start the client: `cd client && python main.py`
2. Drag `b1_sample.zip` onto the drop area
3. Verify results show 13 plant flavors ranked by probability

**Expected top matches:**
- Roman Chamomile Extraction-A (~99%)
- Fig Extraction (~92%)
- Chicory Extraction (~86%)

**API test via curl:**
```bash
curl -X POST http://localhost:8000/api/upload -F "file=@tests/b1_sample.zip"
```

**Folder test:**
Drag the `b1_sample/` folder directly into the client to test folder-based upload.
