# SIH 2026 Regulatory Engine

Deterministic prototype for streamlining industrial approvals, compliance evidence, and government support workflows.

## Current milestones

- Milestone 1: deterministic regulatory applicability engine in `engine-v3/`
- Milestone 2: applicant-facing frontend in `frontend/`
- Milestone 3: deterministic workflow/DAG scheduling in `backend/workflow/`
- Milestone 4: researched document/evidence requirements, submissions, validation, reuse, and readiness
- Milestone 5: not implemented

Architecture:

```text
engine-v3 → M3 workflow → M4 document/evidence layer → future M5 verification
```

`engine-v3/` is protected. M4 does not change applicability, regulatory rules, or workflow scheduling. M4 uploads are not authenticity verification.

## Setup and commands

For prerequisites, virtual-environment setup, exact run commands, and the complete test matrix, see [REQUIREMENTS.md](REQUIREMENTS.md).

Quick start from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
uvicorn backend.main:app --reload --port 8000
```

Run the frontend in a second terminal from `frontend/`:

```powershell
npm run dev
```

The backend is available at `http://127.0.0.1:8000`; the frontend is available at `http://localhost:5173`.

## Testing

```powershell
cd engine-v3
python validate.py
python -m tests.test_engine
python -m tests.test_derived
cd ..
python -m unittest discover -s backend/tests -v
cd frontend
npx tsc --noEmit
```

The frontend production build is intentionally not part of the documented verification command in this repository.

## Backend API

Existing endpoints include `/api/evaluate`, `/api/workflow`, and `/api/evaluate-with-workflow`. M4 adds document requirements, submission, and readiness endpoints under `/api/documents/`.

Detailed contracts are documented in:

- [docs/WORKFLOW_CONTRACT.md](docs/WORKFLOW_CONTRACT.md)
- [docs/DOCUMENT_CONTRACT.md](docs/DOCUMENT_CONTRACT.md)
