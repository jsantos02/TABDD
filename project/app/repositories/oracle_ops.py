# project/app/repositories/oracle_ops.py
from typing import List, Dict
from sqlalchemy import text
from app.db.oracle import get_engine

def get_all_drivers() -> List[Dict]:
    sql = text("SELECT driver_id, license_no FROM drivers ORDER BY driver_id")
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(sql).mappings().all()]

def get_active_vehicles() -> List[Dict]:
    sql = text("SELECT vehicle_id, plate, model FROM vehicles WHERE active=1 ORDER BY plate")
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(sql).mappings().all()]

def create_assignment(assignment_id: str, driver_id: str, vehicle_id: str, line_id: str):
    sql = text("""
        INSERT INTO driver_assignments (
            assignment_id, driver_id, vehicle_id, line_id, start_ts
        ) VALUES (
            :aid, :did, :vid, :lid, SYSTIMESTAMP
        )
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, {
            "aid": assignment_id, "did": driver_id, "vid": vehicle_id, "lid": line_id
        })

# active driver assignemnts by line
def get_active_assignments(line_id: str) -> Dict[str, Dict]:
    sql = text("""
        SELECT assignment_id, vehicle_id, driver_id
        FROM driver_assignments
        WHERE line_id = :lid
          AND start_ts <= SYSTIMESTAMP
          AND (end_ts IS NULL OR end_ts > SYSTIMESTAMP)
    """)
    
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"lid": line_id}).mappings().all()
        
    return {
        str(row["vehicle_id"]): {
            "assignment_id": str(row["assignment_id"]), 
            "driver_id": str(row["driver_id"])
        }
        for row in rows
    }