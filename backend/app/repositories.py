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


def create_analysis_run(
    project_id: int,
    *,
    baseline_document_id: int | None = None,
    pipeline_version: str = "v2",
) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analysis_runs (
                    project_id,
                    baseline_document_id,
                    status,
                    pipeline_version,
                    stage,
                    human_review_status,
                    current_iteration
                )
                VALUES (%s, %s, 'pending', %s, 'extraction', 'not_requested', 1)
                RETURNING id, project_id, baseline_document_id, status, pipeline_version, stage, human_review_status,
                          current_iteration, summary, result_path, error_message, review_artifacts,
                          agent_feedback, human_feedback, step_results, created_at, updated_at;
                """,
                (project_id, baseline_document_id, pipeline_version),
            )
            row = cur.fetchone()
        conn.commit()

    return _analysis_run_row_to_dict(row)


def update_analysis_run(
    run_id: int,
    *,
    status: str,
    stage: str | None = None,
    human_review_status: str | None = None,
    current_iteration: int | None = None,
    baseline_document_id: int | None = None,
    summary: str | None = None,
    result_path: str | None = None,
    error_message: str | None = None,
    review_artifacts: list[dict[str, Any]] | None = None,
    agent_feedback: dict[str, Any] | None = None,
    human_feedback: dict[str, Any] | None = None,
    step_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE analysis_runs
                SET
                    status = %s,
                    stage = COALESCE(%s, stage),
                    human_review_status = COALESCE(%s, human_review_status),
                    current_iteration = COALESCE(%s, current_iteration),
                    baseline_document_id = COALESCE(%s, baseline_document_id),
                    summary = %s,
                    result_path = %s,
                    error_message = %s,
                    review_artifacts = %s::jsonb,
                    agent_feedback = %s::jsonb,
                    human_feedback = %s::jsonb,
                    step_results = %s::jsonb,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, project_id, baseline_document_id, status, pipeline_version, stage, human_review_status,
                          current_iteration, summary, result_path, error_message, review_artifacts,
                          agent_feedback, human_feedback, step_results, created_at, updated_at;
                """,
                (
                    status,
                    stage,
                    human_review_status,
                    current_iteration,
                    baseline_document_id,
                    summary,
                    result_path,
                    error_message,
                    json.dumps(review_artifacts or []),
                    json.dumps(agent_feedback or {}),
                    json.dumps(human_feedback or {}),
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
                SELECT id, project_id, baseline_document_id, status, pipeline_version, stage, human_review_status,
                       current_iteration, summary, result_path, error_message, review_artifacts,
                       agent_feedback, human_feedback, step_results, created_at, updated_at
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
                SELECT id, project_id, baseline_document_id, status, pipeline_version, stage, human_review_status,
                       current_iteration, summary, result_path, error_message, review_artifacts,
                       agent_feedback, human_feedback, step_results, created_at, updated_at
                FROM analysis_runs
                WHERE project_id = %s
                ORDER BY id DESC;
                """,
                (project_id,),
            )
            rows = cur.fetchall()

    return [_analysis_run_row_to_dict(row) for row in rows]


def _loads_if_needed(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def _analysis_run_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "project_id": row[1],
        "baseline_document_id": row[2],
        "status": row[3],
        "pipeline_version": row[4],
        "stage": row[5],
        "human_review_status": row[6],
        "current_iteration": row[7],
        "summary": row[8],
        "result_path": row[9],
        "error_message": row[10],
        "review_artifacts": _loads_if_needed(row[11], []),
        "agent_feedback": _loads_if_needed(row[12], {}),
        "human_feedback": _loads_if_needed(row[13], {}),
        "step_results": _loads_if_needed(row[14], []),
        "created_at": str(row[15]),
        "updated_at": str(row[16]),
    }
