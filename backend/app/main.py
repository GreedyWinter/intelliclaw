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
    
@app.post("/projects/{name}")
def create_project(name: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES (%s) RETURNING id, name, created_at;",
                    (name,)
                )
                row = cur.fetchone()
            conn.commit()
        return {
            "id": row[0],
            "name": row[1],
            "created_at": str(row[2])
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/projects")
def get_projects():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, created_at FROM projects ORDER BY id;")
                rows = cur.fetchall()
        return [
            {"id": row[0], "name": row[1], "created_at": str(row[2])}
            for row in rows
        ]
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/documents")
def get_documents():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, project_id, filename, created_at FROM documents ORDER BY id;"
                )
                rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "project_id": row[1],
                "filename": row[2],
                "created_at": str(row[3]),
            }
            for row in rows
        ]
    except Exception as e:
        return {"error": str(e)}