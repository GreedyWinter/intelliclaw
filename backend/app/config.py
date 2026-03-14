import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path(
    os.getenv("INTELLICLAW_WORKSPACE_DIR", BASE_DIR / "workspace")
).resolve()
UPLOADS_ROOT = WORKSPACE_ROOT / "uploads"
RUNS_ROOT = WORKSPACE_ROOT / "runs"
