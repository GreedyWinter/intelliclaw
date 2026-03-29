import json
from pathlib import Path
from uuid import uuid4

from backend.app.config import RUNS_ROOT, UPLOADS_ROOT, WORKSPACE_ROOT


def ensure_workspace() -> None:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)


def ensure_project_upload_dir(project_id: int) -> Path:
    ensure_workspace()
    path = UPLOADS_ROOT / f"project_{project_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_run_dir(project_id: int, run_id: int) -> Path:
    ensure_workspace()
    path = RUNS_ROOT / f"project_{project_id}" / f"run_{run_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_upload_path(project_id: int, original_filename: str) -> Path:
    suffix = Path(original_filename).suffix.lower()
    safe_name = Path(original_filename).stem.replace(" ", "_")
    return ensure_project_upload_dir(project_id) / f"{safe_name}_{uuid4().hex[:8]}{suffix}"


def get_run_trace_path(run_dir: Path) -> Path:
    return run_dir / "agent_trace.jsonl"


def get_run_summary_path(run_dir: Path) -> Path:
    return run_dir / "run_summary.json"


def append_run_trace(run_dir: Path, entry: dict) -> Path:
    trace_path = get_run_trace_path(run_dir)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str))
        handle.write("\n")
    return trace_path


def write_run_summary(run_dir: Path, payload: dict) -> Path:
    summary_path = get_run_summary_path(run_dir)
    summary_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return summary_path


def read_run_trace(run_dir: Path, *, tail: int | None = None) -> list[dict]:
    trace_path = get_run_trace_path(run_dir)
    if not trace_path.exists():
        return []

    entries: list[dict] = []
    with trace_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({"event_type": "log_parse_error", "message": line})

    if tail is not None and tail >= 0:
        return entries[-tail:]
    return entries


def read_run_summary(run_dir: Path) -> dict:
    summary_path = get_run_summary_path(run_dir)
    if not summary_path.exists():
        return {}

    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
