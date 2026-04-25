# Intelliclaw

Intelliclaw is a Kaggle-to-product migration: a Flutter web frontend plus a FastAPI backend for comparing multiple product specification PDFs and surfacing meaningful feature gaps.

## What It Does

The current iteration lets you:

- create research projects
- upload competitor or reference PDFs
- choose a baseline PDF for comparison
- run a multi-agent extraction workflow
- review reconstructed extraction results before approval
- generate a normalized gap matrix across approved documents
- generate a human-readable gap summary highlighting shared capabilities, baseline differentiators, and baseline gaps

## Current Architecture

### Frontend

- `frontend/`: Flutter web app for project management, uploads, run status, human review, trace visibility, and gap-summary viewing

### Backend

- `backend/`: FastAPI service backed by PostgreSQL
- `backend/workspace/uploads/`: uploaded project PDFs
- `backend/workspace/runs/`: run folders containing intermediate artifacts, logs, canonical CSVs, gap matrix, and gap summary

### Prototype Source

- `intelliclaw.ipynb`: original Kaggle notebook prototype that inspired the orchestration design

## Agent Pipeline

The backend now uses a root orchestrator with explicit sub-agents:

1. `document_listing_agent`
2. `table_extraction_agent`
3. `text_extraction_agent`
4. `sentence_rewrite_agent`
5. `reconstruction_agent`
6. `grammar_evaluator_agent`
7. `coverage_evaluator_agent`
8. `extraction_evaluator_agent`
9. `human_review_preparation_agent`
10. `normalization_agent`
11. `comparison_agent`
12. `gap_summary_agent`
13. `reporting_agent`

## Gemini Usage

The following agents can use Gemini when `GOOGLE_API_KEY` is configured:

- `sentence_rewrite_agent`
- `reconstruction_agent`
- `grammar_evaluator_agent`
- `extraction_evaluator_agent`
- `gap_summary_agent`

The following agents are still deterministic and local:

- `table_extraction_agent`
- `text_extraction_agent`
- `normalization_agent`
- `comparison_agent`
- `reporting_agent`

## Run Flow

The current flow is:

1. upload PDFs into a project
2. choose one PDF as the baseline for comparison
3. extract raw text and table evidence from each PDF
4. rewrite extracted fragments into readable sentences
5. reconstruct one canonical extraction CSV per PDF
6. evaluate the extraction with specialist and aggregate evaluators
7. pause for human review
8. normalize approved capabilities into comparison keys
9. build `gap_matrix.csv`
10. build `gap_summary.md`

## Observability

Each run folder contains artifacts such as:

- `agent_trace.jsonl`
- `run_summary.json`
- raw extraction CSVs
- sentence-stage CSVs
- canonical extraction CSVs
- `gap_matrix.csv`
- `gap_summary.md`

The API also exposes trace and summary information through:

- `GET /agents`
- `GET /projects/{project_id}`
- `GET /projects/{project_id}/analysis-runs`
- `GET /analysis-runs/{run_id}`
- `GET /analysis-runs/{run_id}/trace`

## Secrets

Secrets are not stored in tracked source files.

- Gemini is loaded from `backend/.env`
- the repository ignores `backend/.env`
- this keeps `GOOGLE_API_KEY` hidden when pushing to a public GitHub repo

## Run Locally

Backend:

```powershell
backend\.venv\Scripts\python.exe -m backend.app.init_db
.\backend\run_backend.ps1
```

Frontend web:

```powershell
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## Current Output Expectation

For a successful run, you should expect:

- one approved canonical extraction CSV per PDF
- one normalized CSV per approved PDF
- one `gap_matrix.csv` for the baseline-driven comparison
- one `gap_summary.md` describing common capabilities, baseline gaps, and baseline differentiators

## Next Likely Improvements

- render the gap summary and matrix more richly in the Flutter UI
- add better semantic grouping so equivalent features align more reliably across vendors
- add specialized extractors for brochures, datasheets, and image-heavy PDFs
- add authentication before broader sharing
