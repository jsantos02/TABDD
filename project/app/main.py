from fastapi import FastAPI
from sqlalchemy import text

from app.db.oracle import get_engine

app = FastAPI(title="Test App")

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI + Oracle"}


@app.get("/db-test")
def db_test():
    try:
        with get_engine().begin() as conn:
            result = conn.execute(text("SELECT 'OK' AS status, SYSDATE AS now FROM dual"))
            row = result.fetchone()
        return {
            "ok": True,
            "status": row.status,
            "now": str(row.now),
        }
    except Exception as e:
        # This will tell you if service name / credentials / network are wrong
        return {"ok": False, "error": str(e)}
