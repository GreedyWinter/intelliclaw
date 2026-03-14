from backend.app.db import get_connection

def list_documents():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, project_id, filename, created_at FROM documents ORDER BY id;")
            rows = cur.fetchall()
    return rows

if __name__ == "__main__":
    for row in list_documents():
        print(row)