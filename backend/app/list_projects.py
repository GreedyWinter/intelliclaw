from backend.app.db import get_connection

def list_projects():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM projects ORDER BY id;")
            rows = cur.fetchall()
    return rows

if __name__ == "__main__":
    for row in list_projects():
        print(row)