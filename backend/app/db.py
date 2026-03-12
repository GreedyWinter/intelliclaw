from dotenv import load_dotenv
from pathlib import Path
import os
import psycopg

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg.connect(database_url)