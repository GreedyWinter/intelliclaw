import json
from typing import Any

from fastapi import HTTPException

from backend.app.db import get_connection


def fetch_project(project_id: int) -> dict[str, Any]:
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
                WHERE p.id = %s
                GROUP BY p.id, p.name, p.created_at;
                """,
                (project_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Project not found.")

    return {
        "id": row[0],
        "name": row[1],
        "created_at": str(row[2]),
        "document_count": row[3],
    }


def fetch_project_documents(project_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, project_id, filename, file_path, content_type, size_bytes, status, created_at
                FROM documents
                WHERE project_id = %s
                ORDER BY id DESC;
                """,
                (project_id,),
            )
            rows = cur.fetchall()

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


def create_document(
    project_id: int,
    filename: str,
    file_path: str,
    content_type: str | None,
    size_bytes: int,
) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (project_id, filename, file_path, content_type, size_bytes, status)
                VALUES (%s, %s, %s, %s, %s, 'uploaded')
                RETURNING id, project_id, filename, file_path, content_type, size_bytes, status, created_at;
                """,
                (project_id, filename, file_path, content_type, size_bytes),
            )
            row = cur.fetchone()
        conn.commit()

    return {
        "id": row[0],
        "project_id": row[1],
        "filename": row[2],
        "file_path": row[3],
        "content_type": row[4],
        "size_bytes": row[5],
        "status": row[6],
        "created_at": str(row[7]),
    }


def create_analysis_run(project_id: int, pipeline_version: str = "v1") -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analysis_runs (project_id, status, pipeline_version)
                VALUES (%s, 'pending', %s)
                RETURNING id, project_id, status, pipeline_version, summary, result_path,
                          error_message, step_results, created_at, updated_at;
                """,
                (project_id, pipeline_version),
            )
            row = cur.fetchone()
        conn.commit()

    return _analysis_run_row_to_dict(row)


def update_analysis_run(
    run_id: int,
    *,
    status: str,
    summary: str | None = None,
    result_path: str | None = None,
    error_message: str | None = None,
    step_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE analysis_runs
                SET
                    status = %s,
                    summary = %s,
                    result_path = %s,
                    error_message = %s,
                    step_results = %s::jsonb,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, project_id, status, pipeline_version, summary, result_path,
                          error_message, step_results, created_at, updated_at;
                """,
                (
                    status,
                    summary,
                    result_path,
                    error_message,
                    json.dumps(step_results or []),
                    run_id,
                ),
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    return _analysis_run_row_to_dict(row)


def fetch_analysis_run(run_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, project_id, status, pipeline_version, summary, result_path,
                       error_message, step_results, created_at, updated_at
                FROM analysis_runs
                WHERE id = %s;
                """,
                (run_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    return _analysis_run_row_to_dict(row)


def fetch_project_analysis_runs(project_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, project_id, status, pipeline_version, summary, result_path,
                       error_message, step_results, created_at, updated_at
                FROM analysis_runs
                WHERE project_id = %s
                ORDER BY id DESC;
                """,
                (project_id,),
            )
            rows = cur.fetchall()

    return [_analysis_run_row_to_dict(row) for row in rows]


def _analysis_run_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    step_results = row[7]
    if isinstance(step_results, str):
        step_results = json.loads(step_results)

    return {
        "id": row[0],
        "project_id": row[1],
        "status": row[2],
        "pipeline_version": row[3],
        "summary": row[4],
        "result_path": row[5],
        "error_message": row[6],
        "step_results": step_results or [],
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
    }
