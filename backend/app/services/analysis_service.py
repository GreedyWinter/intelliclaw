from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.agents.base import AnalysisContext, ReviewArtifact
from backend.app.agents.orchestrator import ProductGapOrchestrator
from backend.app.repositories import (
    create_analysis_run,
    fetch_analysis_run,
    fetch_project,
    fetch_project_documents,
    update_analysis_run,
)
from backend.app.storage import write_run_summary, ensure_run_dir


def start_project_analysis(
    project_id: int,
    prompt: str,
    baseline_document_id: int | None = None,
) -> dict[str, Any]:
    fetch_project(project_id)
    documents = fetch_project_documents(project_id)
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="Upload at least one document before starting an analysis run.",
        )

    if baseline_document_id is None:
        baseline_document_id = min(documents, key=lambda item: item["id"])["id"]
    elif baseline_document_id not in {document["id"] for document in documents}:
        raise HTTPException(
            status_code=400,
            detail="Selected baseline document does not belong to this project.",
        )
    analysis_run = create_analysis_run(
        project_id,
        baseline_document_id=baseline_document_id,
    )
    return _run_extraction_and_prepare_review(
        run_id=analysis_run["id"],
        project_id=project_id,
        prompt=prompt,
        documents=documents,
        baseline_document_id=baseline_document_id,
        current_iteration=1,
        agent_feedback={},
        human_feedback={},
    )


def submit_human_review(run_id: int, approved: bool, feedback: str) -> dict[str, Any]:
    run = fetch_analysis_run(run_id)
    if run["human_review_status"] != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail="This analysis run is not waiting for human review.",
        )

    if approved:
        return _resume_gap_analysis_after_approval(run)

    feedback_text = feedback.strip()
    if not feedback_text:
        raise HTTPException(
            status_code=400,
            detail="Feedback is required when requesting another extraction pass.",
        )

    documents = fetch_project_documents(run["project_id"])
    human_feedback = dict(run["human_feedback"])
    for artifact in run["review_artifacts"]:
        document_key = str(artifact["document_id"])
        document_feedback = list(human_feedback.get(document_key, []))
        document_feedback.append(feedback_text)
        human_feedback[document_key] = list(dict.fromkeys(document_feedback))

    return _run_extraction_and_prepare_review(
        run_id=run_id,
        project_id=run["project_id"],
        prompt=run["summary"] or "Human review requested another extraction pass.",
        documents=documents,
        baseline_document_id=run["baseline_document_id"],
        current_iteration=run["current_iteration"] + 1,
        agent_feedback=dict(run["agent_feedback"]),
        human_feedback=human_feedback,
    )


def _run_extraction_and_prepare_review(
    *,
    run_id: int,
    project_id: int,
    prompt: str,
    documents: list[dict[str, Any]],
    baseline_document_id: int | None,
    current_iteration: int,
    agent_feedback: dict[str, list[str]],
    human_feedback: dict[str, list[str]],
) -> dict[str, Any]:
    run_dir = ensure_run_dir(project_id, run_id)
    context = AnalysisContext(
        project_id=project_id,
        run_id=run_id,
        prompt=prompt,
        workspace_dir=run_dir,
        documents=documents,
        baseline_document_id=baseline_document_id,
        current_iteration=current_iteration,
        agent_feedback_history=agent_feedback,
        human_feedback_history=human_feedback,
    )
    orchestrator = ProductGapOrchestrator()
    context.log_event(
        source="analysis_service",
        target="product_gap_root_orchestrator",
        event_type="run_started",
        message="Starting extraction stage for this analysis run.",
        payload={
            "project_id": project_id,
            "run_id": run_id,
            "current_iteration": current_iteration,
            "document_count": len(documents),
            "baseline_document_id": baseline_document_id,
        },
    )

    update_analysis_run(
        run_id,
        status="running",
        stage="extraction",
        human_review_status="not_requested",
        current_iteration=current_iteration,
        baseline_document_id=baseline_document_id,
    )

    try:
        context = orchestrator.run_until_human_review(context)
    except HTTPException as exc:
        context.log_event(
            source="analysis_service",
            target=None,
            event_type="run_failed",
            message="Extraction stage ended in failure before human review.",
            payload={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "failure_details": context.failure_details,
            },
        )
        _write_run_summary(
            context,
            status="failed",
            stage="extraction",
            human_review_status="not_requested",
            error_message=str(exc.detail),
        )
        return update_analysis_run(
            run_id,
            status="failed",
            stage="extraction",
            human_review_status="not_requested",
            current_iteration=current_iteration,
            summary=_build_failure_summary(context, str(exc.detail)),
            error_message=str(exc.detail),
            agent_feedback=context.agent_feedback_history,
            human_feedback=context.human_feedback_history,
            step_results=_serialize_step_results(context),
        )
    except Exception as exc:
        context.log_event(
            source="analysis_service",
            target=None,
            event_type="run_failed",
            message="Extraction stage raised an unexpected exception before human review.",
            payload={"detail": str(exc), "failure_details": context.failure_details},
        )
        _write_run_summary(
            context,
            status="failed",
            stage="extraction",
            human_review_status="not_requested",
            error_message=str(exc),
        )
        return update_analysis_run(
            run_id,
            status="failed",
            stage="extraction",
            human_review_status="not_requested",
            current_iteration=current_iteration,
            summary=_build_failure_summary(context, str(exc)),
            error_message=str(exc),
            agent_feedback=context.agent_feedback_history,
            human_feedback=context.human_feedback_history,
            step_results=_serialize_step_results(context),
        )

    context.log_event(
        source="analysis_service",
        target="human_reviewer",
        event_type="awaiting_human_review",
        message="Extraction stage completed successfully and is waiting for human review.",
        payload={"review_artifact_count": len(context.review_artifacts)},
    )
    _write_run_summary(
        context,
        status="awaiting_human_review",
        stage="human_review",
        human_review_status="awaiting_review",
        summary=(
            "Evaluator-approved extraction is ready for human review. Review the preview rows "
            "and either approve them or request another pass with feedback."
        ),
    )
    return update_analysis_run(
        run_id,
        status="awaiting_human_review",
        stage="human_review",
        human_review_status="awaiting_review",
        current_iteration=current_iteration,
        summary=(
            "Evaluator-approved extraction is ready for human review. Review the preview rows "
            "and either approve them or request another pass with feedback."
        ),
        review_artifacts=_serialize_review_artifacts(context.review_artifacts),
        agent_feedback=context.agent_feedback_history,
        human_feedback=context.human_feedback_history,
        step_results=_serialize_step_results(context),
    )


def _resume_gap_analysis_after_approval(run: dict[str, Any]) -> dict[str, Any]:
    documents = fetch_project_documents(run["project_id"])
    run_dir = ensure_run_dir(run["project_id"], run["id"])
    context = AnalysisContext(
        project_id=run["project_id"],
        run_id=run["id"],
        prompt=run["summary"] or "",
        workspace_dir=run_dir,
        documents=documents,
        baseline_document_id=run["baseline_document_id"],
        current_iteration=run["current_iteration"],
        agent_feedback_history=dict(run["agent_feedback"]),
        human_feedback_history=dict(run["human_feedback"]),
        review_artifacts=[
            ReviewArtifact(
                document_id=artifact["document_id"],
                filename=artifact["filename"],
                csv_path=Path(artifact["csv_path"]),
                preview_rows=list(artifact.get("preview_rows", [])),
                evaluator_feedback=list(artifact.get("evaluator_feedback", [])),
                human_feedback=list(artifact.get("human_feedback", [])),
                approved=True,
            )
            for artifact in run["review_artifacts"]
        ],
    )

    orchestrator = ProductGapOrchestrator()
    context.log_event(
        source="analysis_service",
        target="product_gap_root_orchestrator",
        event_type="resume_requested",
        message="Human review approved the extraction. Resuming gap analysis.",
        payload={"run_id": run["id"], "project_id": run["project_id"]},
    )
    update_analysis_run(
        run["id"],
        status="running",
        stage="gap_analysis",
        human_review_status="approved",
        current_iteration=run["current_iteration"],
        review_artifacts=run["review_artifacts"],
        agent_feedback=run["agent_feedback"],
        human_feedback=run["human_feedback"],
        step_results=run["step_results"],
    )

    try:
        context = orchestrator.resume_after_human_approval(context)
    except HTTPException as exc:
        context.log_event(
            source="analysis_service",
            target=None,
            event_type="run_failed",
            message="Gap analysis failed after human approval.",
            payload={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "failure_details": context.failure_details,
            },
        )
        _write_run_summary(
            context,
            status="failed",
            stage="gap_analysis",
            human_review_status="approved",
            error_message=str(exc.detail),
        )
        return update_analysis_run(
            run["id"],
            status="failed",
            stage="gap_analysis",
            human_review_status="approved",
            current_iteration=run["current_iteration"],
            summary=_build_failure_summary(context, str(exc.detail)),
            error_message=str(exc.detail),
            review_artifacts=run["review_artifacts"],
            agent_feedback=run["agent_feedback"],
            human_feedback=run["human_feedback"],
            step_results=[*run["step_results"], *_serialize_step_results(context)],
        )
    except Exception as exc:
        context.log_event(
            source="analysis_service",
            target=None,
            event_type="run_failed",
            message="Gap analysis raised an unexpected exception after human approval.",
            payload={"detail": str(exc), "failure_details": context.failure_details},
        )
        _write_run_summary(
            context,
            status="failed",
            stage="gap_analysis",
            human_review_status="approved",
            error_message=str(exc),
        )
        return update_analysis_run(
            run["id"],
            status="failed",
            stage="gap_analysis",
            human_review_status="approved",
            current_iteration=run["current_iteration"],
            summary=_build_failure_summary(context, str(exc)),
            error_message=str(exc),
            review_artifacts=run["review_artifacts"],
            agent_feedback=run["agent_feedback"],
            human_feedback=run["human_feedback"],
            step_results=[*run["step_results"], *_serialize_step_results(context)],
        )

    context.log_event(
        source="analysis_service",
        target=None,
        event_type="run_completed",
        message="Gap analysis completed successfully.",
        payload={"result_path": str(context.gap_matrix_path) if context.gap_matrix_path else None},
    )
    _write_run_summary(
        context,
        status="completed",
        stage="completed",
        human_review_status="approved",
        summary=context.summary,
        result_path=str(context.gap_matrix_path) if context.gap_matrix_path else None,
    )
    return update_analysis_run(
        run["id"],
        status="completed",
        stage="completed",
        human_review_status="approved",
        current_iteration=run["current_iteration"],
        summary=context.summary,
        result_path=str(context.gap_matrix_path) if context.gap_matrix_path else None,
        review_artifacts=run["review_artifacts"],
        agent_feedback=context.agent_feedback_history,
        human_feedback=context.human_feedback_history,
        step_results=[*run["step_results"], *_serialize_step_results(context)],
    )


def _serialize_step_results(context: AnalysisContext) -> list[dict[str, Any]]:
    return [
        {
            "name": result.name,
            "status": result.status,
            "document_id": result.document_id,
            "attempt": result.attempt,
            "details": result.details,
        }
        for result in context.step_results
    ]


def _serialize_review_artifacts(artifacts: list[ReviewArtifact]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": artifact.document_id,
            "filename": artifact.filename,
            "csv_path": str(artifact.csv_path),
            "preview_rows": artifact.preview_rows,
            "evaluator_feedback": artifact.evaluator_feedback,
            "human_feedback": artifact.human_feedback,
            "approved": artifact.approved,
        }
        for artifact in artifacts
    ]


def _build_failure_summary(context: AnalysisContext, detail: str) -> str:
    if context.failure_details.get("reason") == "extraction_not_approved":
        latest_decision = context.failure_details.get("latest_decision") or {}
        feedback = latest_decision.get("feedback") or context.failure_details.get("feedback_history") or []
        feedback_text = " ".join(str(item) for item in feedback[:3]).strip()
        base = (
            "Extraction stopped before human review because the evaluator could not "
            f"approve {context.failure_details.get('filename', 'the document')}."
        )
        if feedback_text:
            return f"{base} Latest evaluator feedback: {feedback_text}"
        return base
    return detail


def _write_run_summary(
    context: AnalysisContext,
    *,
    status: str,
    stage: str,
    human_review_status: str,
    summary: str | None = None,
    error_message: str | None = None,
    result_path: str | None = None,
) -> None:
    write_run_summary(
        context.workspace_dir,
        {
            "project_id": context.project_id,
            "run_id": context.run_id,
            "baseline_document_id": context.baseline_document_id,
            "status": status,
            "stage": stage,
            "human_review_status": human_review_status,
            "summary": summary,
            "error_message": error_message,
            "result_path": result_path,
            "current_iteration": context.current_iteration,
            "failure_details": context.failure_details,
            "agent_feedback_history": context.agent_feedback_history,
            "human_feedback_history": context.human_feedback_history,
            "step_results": _serialize_step_results(context),
            "trace_event_count": len(context.agent_trace),
        },
    )
