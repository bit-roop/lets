# Repository Requirements and Setup

This guide describes the tested setup for a fresh Windows clone of the repository.

## System prerequisites

- Git, with access to clone the repository.
- Python 3.10 or newer. The current environment was tested with Python 3.12.10; the repository does not enforce an exact patch version.
- Node.js/npm for the Vite frontend. The current environment was tested with Node.js v22.19.0 and npm 11.18.0. The package does not declare an exact Node version; use a current supported Node LTS release.
- PowerShell or another terminal capable of running the commands below.

No database, Docker service, external API key, or separate engine installation is required.

## Repository structure

```text
engine-v3/              protected deterministic applicability engine
backend/                FastAPI adapter and API
backend/workflow/       Milestone 3 workflow/DAG layer
backend/documents/      Milestone 4 evidence/readiness layer
frontend/               Milestone 2 applicant UI
regulatory-documents/   M4 source-backed document catalogue
docs/                   workflow and document contracts
```

The runtime direction is:

```text
engine-v3 → M3 workflow → M4 document/evidence layer → future M5 verification
```

`engine-v3/` is protected. M3 and M4 are downstream and must not alter engine applicability or regulatory rules. M5 is not implemented.

## Backend setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

The dependency file includes FastAPI, Uvicorn, Pydantic, Requests, and `python-multipart` for multipart form parsing.

## Frontend setup

```powershell
cd frontend
npm install
```

The frontend uses Vite. Its development server is configured for port `5173` and proxies `/api` to the backend at port `8000`.

## Running the application

Start the backend from the repository root in one terminal:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Backend URLs:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Start the frontend from `frontend/` in a second terminal:

```powershell
npm run dev
```

Frontend URL: `http://localhost:5173`.

## Validation and tests

Engine validation and core tests:

```powershell
cd engine-v3
python validate.py
python -m tests.test_engine
python -m tests.test_derived
```

Engine demo:

```powershell
python demo_derived.py
```

Backend tests, including M3 and M4:

```powershell
cd ..
python -m unittest discover -s backend/tests -v
```

M3-specific tests:

```powershell
python -m unittest backend.tests.test_workflow_graph backend.tests.test_workflow_scheduler backend.tests.test_workflow_policy backend.tests.test_workflow_api backend.tests.test_workflow_regression -v
```

M4-specific tests:

```powershell
python -m unittest backend.tests.test_m4_documents -v
```

Frontend TypeScript validation:

```powershell
cd frontend
npx tsc --noEmit
```

The repository instruction is not to run `npm run build`; it is not part of this setup guide.

## Current milestone status

- M1 is complete under `engine-v3/`.
- M2 frontend behavior is complete and unchanged by M4.
- M3 workflow scheduling is complete under `backend/workflow/`.
- M4 is implemented and hardened for researched evidence requirements, submissions, deterministic format checks, reuse, and readiness.
- M5 is not implemented.

## M4 scope and limitations

M4 covers only source-backed evidence data for F-02, S-02, and S-03. The other current approvals remain explicitly unsupported. S-03 technical-document requirements remain unsupported where the research did not establish an itemized official checklist.

M4 may record file presence, filename, size, MIME type, SHA-256, timestamp, structured fields, and duplicate identity. A checksum or format check does not establish authenticity, government issuance, ownership, or current regulatory validity.

The following are not implemented and belong to M5 or later:

- OCR or semantic PDF/image extraction
- AI or LLM document classification
- authenticity, issuer, QR, or signature verification
- government API integrations
- DigiLocker, GSTN, MCA, EPFO, or ESIC verification

Current MVP limitations include no authentication/authorization, temporary/in-memory submission storage, limited format validators, and no frontend document UI.

## Detailed contracts

- [Workflow contract](docs/WORKFLOW_CONTRACT.md)
- [Document contract](docs/DOCUMENT_CONTRACT.md)
- [Backend documentation](backend/README.md)
