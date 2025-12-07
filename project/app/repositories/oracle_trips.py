# project/app/repositories/oracle_trips.py
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import text
from app.db.oracle import get_engine

def create_trip(trip_id: str, user_id: str, data: Dict):
    sql = text("""
        INSERT INTO trips (
            trip_id, user_id, line_id, origin_stop_id, dest_stop_id,
            planned_start, planned_end, created_at
        ) VALUES (
            :tid, :uid, :lid, :oid, :did, :start, :end, :created
        )
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, {
            "tid": trip_id, "uid": user_id, "lid": data.line_id,
            "oid": data.origin_stop_id, "did": data.dest_stop_id,
            "start": data.planned_start, "end": data.planned_end,
            "created": datetime.utcnow()
        })

def get_user_history(user_id: str, limit: int = 20) -> List[Dict]:
    sql = text("""
        SELECT t.trip_id, t.planned_start, t.planned_end, t.line_id,
               o.name AS origin_name, d.name AS dest_name
        FROM trips t
        LEFT JOIN stops o ON t.origin_stop_id = o.stop_id
        LEFT JOIN stops d ON t.dest_stop_id = d.stop_id
        WHERE t.user_id = :uid
        ORDER BY t.planned_start DESC
        FETCH FIRST :lim ROWS ONLY
    """)
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(sql, {"uid": user_id, "lim": limit}).mappings().all()]