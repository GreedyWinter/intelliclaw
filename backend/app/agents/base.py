from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.storage import append_run_trace


@dataclass
class AgentStepResult:
    name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)
    document_id: int | None = None
    attempt: int | None = None


@dataclass
class ExtractionCandidate:
    document_id: int
    strategy: str
    source_kind: str
    csv_path: Path
    row_count: int
    metrics: dict[str, float] = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)


@dataclass
class ReviewArtifact:
    document_id: int
    filename: str
    csv_path: Path
    preview_rows: list[dict[str, Any]]
    evaluator_feedback: list[str]
    human_feedback: list[str]
    approved: bool = False


@dataclass
class EvaluationDecision:
    document_id: int
    accepted: bool
    chosen_strategy: str | None
    chosen_csv_path: Path | None
    score: float
    retry_requested: bool
    feedback: list[str] = field(default_factory=list)


@dataclass
class AnalysisContext:
    project_id: int
    run_id: int
    prompt: str
    workspace_dir: Path
    documents: list[dict[str, Any]]
    current_iteration: int = 1
    listed_documents: list[dict[str, Any]] = field(default_factory=list)
    raw_candidates: dict[int, list[ExtractionCandidate]] = field(default_factory=dict)
    sentence_candidates: dict[int, list[ExtractionCandidate]] = field(default_factory=dict)
    canonical_candidates: dict[int, list[ExtractionCandidate]] = field(default_factory=dict)
    evaluation_decisions: dict[int, EvaluationDecision] = field(default_factory=dict)
    accepted_extractions: dict[int, Path] = field(default_factory=dict)
    review_artifacts: list[ReviewArtifact] = field(default_factory=list)
    agent_feedback_history: dict[str, list[str]] = field(default_factory=dict)
    human_feedback_history: dict[str, list[str]] = field(default_factory=dict)
    normalized_csvs: list[Path] = field(default_factory=list)
    gap_matrix_path: Path | None = None
    summary: str | None = None
    step_results: list[AgentStepResult] = field(default_factory=list)
    agent_trace: list[dict[str, Any]] = field(default_factory=list)
    failure_details: dict[str, Any] = field(default_factory=dict)
    max_extraction_attempts: int = 3

    def log_event(
        self,
        *,
        source: str,
        target: str | None,
        event_type: str,
        message: str,
        document_id: int | None = None,
        attempt: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "source": source,
            "target": target,
            "event_type": event_type,
            "message": message,
            "document_id": document_id,
            "attempt": attempt,
            "payload": payload or {},
        }
        self.agent_trace.append(entry)
        append_run_trace(self.workspace_dir, entry)


class BaseSubAgent:
    name = "base_sub_agent"
    role = "generic"

    def run(self, context: AnalysisContext, **kwargs: Any) -> AgentStepResult:
        raise NotImplementedError
