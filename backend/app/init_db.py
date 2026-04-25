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
                    baseline_document_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending',
                    pipeline_version TEXT NOT NULL DEFAULT 'v1',
                    stage TEXT NOT NULL DEFAULT 'extraction',
                    human_review_status TEXT NOT NULL DEFAULT 'not_requested',
                    current_iteration INTEGER NOT NULL DEFAULT 1,
                    summary TEXT,
                    result_path TEXT,
                    error_message TEXT,
                    review_artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
                    agent_feedback JSONB NOT NULL DEFAULT '{}'::jsonb,
                    human_feedback JSONB NOT NULL DEFAULT '{}'::jsonb,
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
            cur.execute("""
                ALTER TABLE analysis_runs
                ADD COLUMN IF NOT EXISTS baseline_document_id INTEGER;
            """)
            cur.execute("""
                ALTER TABLE analysis_runs
                ADD COLUMN IF NOT EXISTS stage TEXT NOT NULL DEFAULT 'extraction';
            """)
            cur.execute("""
                ALTER TABLE analysis_runs
                ADD COLUMN IF NOT EXISTS human_review_status TEXT NOT NULL DEFAULT 'not_requested';
            """)
            cur.execute("""
                ALTER TABLE analysis_runs
                ADD COLUMN IF NOT EXISTS current_iteration INTEGER NOT NULL DEFAULT 1;
            """)
            cur.execute("""
                ALTER TABLE analysis_runs
                ADD COLUMN IF NOT EXISTS review_artifacts JSONB NOT NULL DEFAULT '[]'::jsonb;
            """)
            cur.execute("""
                ALTER TABLE analysis_runs
                ADD COLUMN IF NOT EXISTS agent_feedback JSONB NOT NULL DEFAULT '{}'::jsonb;
            """)
            cur.execute("""
                ALTER TABLE analysis_runs
                ADD COLUMN IF NOT EXISTS human_feedback JSONB NOT NULL DEFAULT '{}'::jsonb;
            """)
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("database tables created or already exist")
