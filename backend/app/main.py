import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.agent_manifest import get_agent_manifest
from backend.app.db import get_connection
from backend.app.repositories import (
    create_document,
    fetch_analysis_run,
    fetch_project,
    fetch_project_analysis_runs,
    fetch_project_documents,
)
from backend.app.schemas import AnalysisRunCreate, HumanReviewSubmission, ProjectCreate
from backend.app.services.analysis_service import start_project_analysis, submit_human_review
from backend.app.storage import (
    build_upload_path,
    ensure_run_dir,
    ensure_workspace,
    get_run_summary_path,
    get_run_trace_path,
    read_run_summary,
    read_run_trace,
)

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Intelliclaw API")
ensure_workspace()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Intelliclaw backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/agents")
def list_agents():
    return get_agent_manifest()


@app.get("/config-check")
def config_check():
    api_key = os.getenv("GOOGLE_API_KEY")
    return {"gemini_key_loaded": bool(api_key)}


@app.get("/db-check")
def db_check():
    database_url = os.getenv("DATABASE_URL")
    return {"database_url_loaded": bool(database_url)}


@app.get("/db-connect")
def db_connect():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
        return {"connected": True, "version": version}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/projects", status_code=201)
def create_project(payload: ProjectCreate):
    name = payload.name.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty.")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO projects (name)
                    VALUES (%s)
                    RETURNING id, name, created_at;
                    """,
                    (name,),
                )
                row = cur.fetchone()
            conn.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "id": row[0],
        "name": row[1],
        "created_at": str(row[2]),
    }


@app.get("/projects")
def get_projects():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        p.id,
                        p.name,
                        p.created_at,
                        COUNT(d.id) AS document_count
                    FROM projects p
                    LEFT JOIN documents d ON d.project_id = p.id
                    GROUP BY p.id, p.name, p.created_at
                    ORDER BY p.id DESC;
                    """
                )
                rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [
        {
            "id": row[0],
            "name": row[1],
            "created_at": str(row[2]),
            "document_count": row[3],
        }
        for row in rows
    ]


@app.get("/projects/summary")
def get_project_summary():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM projects;")
                project_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM documents;")
                document_count = cur.fetchone()[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "project_count": project_count,
        "document_count": document_count,
    }


@app.get("/projects/{project_id}")
def get_project(project_id: int):
    project = fetch_project(project_id)
    project["documents"] = fetch_project_documents(project_id)
    project["analysis_runs"] = [_with_run_observability(run) for run in fetch_project_analysis_runs(project_id)]
    return project


@app.get("/projects/{project_id}/documents")
def get_project_documents(project_id: int):
    fetch_project(project_id)
    return fetch_project_documents(project_id)


@app.post("/projects/{project_id}/documents", status_code=201)
async def upload_project_document(project_id: int, file: UploadFile = File(...)):
    fetch_project(project_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    destination = build_upload_path(project_id, file.filename)
    content = await file.read()
    destination.write_bytes(content)

    return create_document(
        project_id=project_id,
        filename=file.filename,
        file_path=str(destination),
        content_type=file.content_type,
        size_bytes=len(content),
    )


@app.get("/projects/{project_id}/analysis-runs")
def get_project_runs(project_id: int):
    fetch_project(project_id)
    return [_with_run_observability(run) for run in fetch_project_analysis_runs(project_id)]


@app.post("/projects/{project_id}/analysis-runs", status_code=201)
def create_project_run(project_id: int, payload: AnalysisRunCreate):
    fetch_project(project_id)
    return start_project_analysis(project_id, payload.prompt)


@app.get("/analysis-runs/{run_id}")
def get_analysis_run(run_id: int):
    return _with_run_observability(fetch_analysis_run(run_id))


@app.get("/analysis-runs/{run_id}/trace")
def get_analysis_run_trace(run_id: int):
    run = fetch_analysis_run(run_id)
    run_dir = ensure_run_dir(run["project_id"], run_id)
    return {
        "run_id": run_id,
        "project_id": run["project_id"],
        "trace_path": str(get_run_trace_path(run_dir)),
        "summary_path": str(get_run_summary_path(run_dir)),
        "trace_entries": read_run_trace(run_dir),
        "summary": read_run_summary(run_dir),
    }


@app.post("/analysis-runs/{run_id}/human-review")
def review_analysis_run(run_id: int, payload: HumanReviewSubmission):
    return submit_human_review(run_id, payload.approved, payload.feedback)


@app.get("/documents")
def get_documents():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, project_id, filename, file_path, content_type, size_bytes, status, created_at
                    FROM documents
                    ORDER BY id DESC;
                    """
                )
                rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [
        {
            "id": row[0],
            "project_id": row[1],
            "filename": row[2],
            "file_path": row[3],
            "content_type": row[4],
            "size_bytes": row[5],
            "status": row[6],
            "created_at": str(row[7]),
        }
        for row in rows
    ]


def _with_run_observability(run: dict) -> dict:
    run_dir = ensure_run_dir(run["project_id"], run["id"])
    summary_payload = read_run_summary(run_dir)
    trace_entries = read_run_trace(run_dir, tail=40)
    run["trace_path"] = str(get_run_trace_path(run_dir))
    run["summary_path"] = str(get_run_summary_path(run_dir))
    run["failure_details"] = summary_payload.get("failure_details", {})
    run["trace_preview"] = trace_entries
    run["latest_trace_message"] = trace_entries[-1]["message"] if trace_entries else None
    return run
