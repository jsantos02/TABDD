# project/app/repositories/oracle_lines.py
from typing import List, Dict, Optional
from sqlalchemy import text
from app.db.oracle import get_engine

def get_active_lines() -> List[Dict]:
    sql = text("""
        SELECT line_id, code, name, line_mode, active
        FROM lines
        WHERE active = 1
        ORDER BY line_mode, code
    """)
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(sql).mappings().all()]

def get_all_stops() -> List[Dict]:
    sql = text("SELECT stop_id, code, name, lat, lon FROM stops ORDER BY name")
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(sql).mappings().all()]

def get_line_details(line_id: str) -> Optional[Dict]:
    engine = get_engine()
    with engine.connect() as conn:
        line = conn.execute(
            text("SELECT line_id, code, name, line_mode, active FROM lines WHERE line_id = :lid"),
            {"lid": line_id}
        ).mappings().first()
        
        if not line:
            return None

        stops = conn.execute(
            text("""
                SELECT s.stop_id, s.code, s.name, st.scheduled_seconds_from_start
                FROM stop_times st
                JOIN stops s ON s.stop_id = st.stop_id
                WHERE st.line_id = :lid
                ORDER BY st.scheduled_seconds_from_start
            """),
            {"lid": line_id}
        ).mappings().all()

        schedules = conn.execute(
            text("""
                SELECT dow, TO_CHAR(start_time, 'HH24:MI') as start_str, 
                       TO_CHAR(end_time, 'HH24:MI') as end_str, headway_minutes
                FROM line_schedules
                WHERE line_id = :lid
                ORDER BY dow
            """),
            {"lid": line_id}
        ).mappings().all()

    return {
        "line": dict(line),
        "stops": [dict(s) for s in stops],
        "schedules": [dict(s) for s in schedules]
    }

def get_lines_by_ids(line_ids: List[str]) -> Dict[str, Dict]:
    if not line_ids:
        return {}
    
    # Dynamic parameter binding for list
    binds = {f"l{i}": lid for i, lid in enumerate(line_ids)}
    placeholders = ",".join(f":{k}" for k in binds.keys())
    
    sql = text(f"SELECT line_id, code, name, line_mode FROM lines WHERE line_id IN ({placeholders})")
    
    with get_engine().connect() as conn:
        rows = conn.execute(sql, binds).mappings().all()
        return {row["line_id"]: dict(row) for row in rows}

def get_stops_by_ids(stop_ids: List[str]) -> Dict[str, Dict]:
    if not stop_ids:
        return {}
        
    binds = {f"s{i}": sid for i, sid in enumerate(stop_ids)}
    placeholders = ",".join(f":{k}" for k in binds.keys())
    
    sql = text(f"SELECT stop_id, code, name, lat, lon FROM stops WHERE stop_id IN ({placeholders})")
    
    with get_engine().connect() as conn:
        rows = conn.execute(sql, binds).mappings().all()
        return {row["stop_id"]: dict(row) for row in rows}