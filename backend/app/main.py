from fastapi import FastAPI
from dotenv import load_dotenv
import os

from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Intelliclaw API")

@app.get("/")
def read_root():
    return {"message": "Intelliclaw backend is running"}

@app.get("/config-check")
def config_check():
    api_key = os.getenv("GOOGLE_API_KEY")
    return {"gemini_key_loaded": bool(api_key)}