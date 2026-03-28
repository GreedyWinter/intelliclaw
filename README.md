# Intelliclaw

Intelliclaw is being migrated from a Kaggle notebook prototype into a Flutter + FastAPI application.

## Current shape

- `backend/`: FastAPI service backed by PostgreSQL
- `frontend/`: Flutter app, currently aimed at web-first local development
- `intelliclaw.ipynb`: Kaggle prototype for document comparison and gap analysis using Gemini ADK

## First iteration goal

The first web iteration is intentionally small:

- create and view projects
- confirm backend connectivity from the browser
- upload project documents
- trigger a first-pass analysis run
- prepare the orchestration layer that future Gemini/ADK execution will attach to

## Run locally

Backend:

```powershell
backend\.venv\Scripts\python.exe -m backend.app.init_db
.\backend\run_backend.ps1
```

Frontend web:

```powershell
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## What comes next

The Kaggle notebook already sketches the real product workflow:

1. upload competitor PDFs into a project
2. extract tables from PDFs
3. unify and normalize features
4. generate a gap matrix
5. surface the result in the web app

That notebook logic should move into backend services and job endpoints rather than staying inside notebook cells.

## Orchestration design

The backend now includes a root orchestrator with explicit sub-agents:

1. `document_listing_agent`
2. `pdf_extraction_agent`
3. `normalization_agent`
4. `comparison_agent`
5. `reporting_agent`

This mirrors the Kaggle notebook structure while staying runnable without an ADK dependency.
The API surface for this is:

- `GET /agents`
- `POST /projects/{project_id}/documents`
- `POST /projects/{project_id}/analysis-runs`
- `GET /projects/{project_id}/analysis-runs`
- `GET /analysis-runs/{run_id}`
