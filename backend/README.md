# Regulatory Engine Backend

This FastAPI service wraps the protected deterministic engine in `engine-v3/`, exposes the Milestone 3 workflow, and provides the Milestone 4 document/evidence readiness layer. It does not implement Milestone 5 document authenticity or semantic verification.

## Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

## Run

```powershell
uvicorn backend.main:app --reload --port 8000
```

API documentation is available at `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/redoc`.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Engine health and verification summary |
| GET | `/api/catalogue` | Regulatory catalogue |
| GET | `/api/sources` | Engine sources |
| POST | `/api/evaluate` | Backward-compatible engine evaluation |
| POST | `/api/workflow` | Milestone 3 workflow |
| POST | `/api/evaluate-with-workflow` | Evaluation plus workflow |
| GET/POST | `/api/documents/requirements` | M4 registry and conditional requirements |
| POST | `/api/documents/submit` | M4 metadata or multipart submission |
| GET | `/api/documents/readiness` | M4 readiness result |

M4 supports only the researched F-02, S-02, and S-03 evidence catalogues. Other approvals remain explicitly unsupported. Uploads are recorded as unvalidated evidence; no OCR, authenticity, issuer, or government API verification is performed.

See [docs/WORKFLOW_CONTRACT.md](../docs/WORKFLOW_CONTRACT.md), [docs/DOCUMENT_CONTRACT.md](../docs/DOCUMENT_CONTRACT.md), and [REQUIREMENTS.md](../REQUIREMENTS.md).
