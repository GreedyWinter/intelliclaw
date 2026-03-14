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
