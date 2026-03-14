from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentStepResult:
    name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisContext:
    project_id: int
    run_id: int
    prompt: str
    workspace_dir: Path
    documents: list[dict[str, Any]]
    extracted_csvs: list[Path] = field(default_factory=list)
    normalized_csvs: list[Path] = field(default_factory=list)
    gap_matrix_path: Path | None = None
    summary: str | None = None
    step_results: list[AgentStepResult] = field(default_factory=list)


class BaseSubAgent:
    name = "base_sub_agent"

    def run(self, context: AnalysisContext) -> AgentStepResult:
        raise NotImplementedError
