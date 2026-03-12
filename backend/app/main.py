from fastapi import FastAPI
from dotenv import load_dotenv
from backend.app.db import get_connection
import os
import psycopg

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

@app.get("/db-check")
def db_check():
    database_url = os.getenv("DATABASE_URL")
    return {"database_url_loaded": bool(database_url)}

@app.get("/db-connect")
def db_connect():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
        return {"connected": True, "version": version}
    except Exception as e:
        return {"connected": False, "error": str(e)}