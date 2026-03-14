from backend.app.db import get_connection

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    file_path TEXT,
                    content_type TEXT,
                    size_bytes BIGINT,
                    status TEXT NOT NULL DEFAULT 'uploaded',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    pipeline_version TEXT NOT NULL DEFAULT 'v1',
                    summary TEXT,
                    result_path TEXT,
                    error_message TEXT,
                    step_results JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS file_path TEXT;
            """)
            cur.execute("""
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS content_type TEXT;
            """)
            cur.execute("""
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS size_bytes BIGINT;
            """)
            cur.execute("""
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'uploaded';
            """)
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("database tables created or already exist")
