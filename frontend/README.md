# Intelliclaw Frontend

This Flutter app is the web-first interface for Intelliclaw.

## Current Responsibilities

The frontend currently supports:

- project creation
- project inventory viewing
- PDF upload
- analysis-run execution
- human-in-the-loop review of reconstructed extraction CSVs
- failed-run diagnostics and trace previews
- display of generated gap summaries for completed runs

## Run Locally

```powershell
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## Backend Requirement

The FastAPI backend must already be running on the URL passed through `API_BASE_URL`.

Default:

```text
http://127.0.0.1:8000
```

## Main Screen Flow

1. create or open a project
2. upload one or more PDFs
3. start an analysis run
4. inspect human-review artifacts if the run pauses for review
5. approve or request another extraction pass
6. inspect the final gap summary and run traces
