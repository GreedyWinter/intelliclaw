from fastapi import HTTPException

from backend.app.agents.base import AnalysisContext
from backend.app.agents.orchestrator import ProductGapOrchestrator
from backend.app.repositories import (
    create_analysis_run,
    fetch_project,
    fetch_project_documents,
    update_analysis_run,
)
from backend.app.storage import ensure_run_dir


def run_project_analysis(project_id: int, prompt: str) -> dict:
    project = fetch_project(project_id)
    documents = fetch_project_documents(project_id)

    if not documents:
        raise HTTPException(
            status_code=400,
            detail="Upload at least one document before starting an analysis run.",
        )

    analysis_run = create_analysis_run(project_id)
    run_dir = ensure_run_dir(project_id, analysis_run["id"])

    context = AnalysisContext(
        project_id=project["id"],
        run_id=analysis_run["id"],
        prompt=prompt,
        workspace_dir=run_dir,
        documents=documents,
    )

    orchestrator = ProductGapOrchestrator()

    try:
        update_analysis_run(analysis_run["id"], status="running")
        context = orchestrator.run(context)
        return update_analysis_run(
            analysis_run["id"],
            status="completed",
            summary=context.summary,
            result_path=str(context.gap_matrix_path) if context.gap_matrix_path else None,
            step_results=[
                {
                    "name": result.name,
                    "status": result.status,
                    "details": result.details,
                }
                for result in context.step_results
            ],
        )
    except Exception as exc:
        return update_analysis_run(
            analysis_run["id"],
            status="failed",
            error_message=str(exc),
            step_results=[
                {
                    "name": result.name,
                    "status": result.status,
                    "details": result.details,
                }
                for result in context.step_results
            ],
        )
