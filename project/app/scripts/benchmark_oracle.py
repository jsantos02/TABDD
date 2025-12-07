import sys
import os
import time
from sqlalchemy import text
from app.db.oracle import get_engine

def run_benchmark():
    engine = get_engine()
    
    # This query matches the index: (line_id, start_ts)
    # We look for assignments for LINE_M_A that started after 2024
    sql_with_index = text("""
        SELECT count(*) 
        FROM driver_assignments 
        WHERE line_id = :lid 
          AND start_ts > TO_TIMESTAMP(:ts, 'YYYY-MM-DD HH24:MI:SS')
    """)

    # This forces Oracle to ignore the index and do a FULL TABLE SCAN
    sql_no_index = text("""
        SELECT /*+ NO_INDEX(driver_assignments idx_driver_assignments_active) */ count(*) 
        FROM driver_assignments 
        WHERE line_id = :lid 
          AND start_ts > TO_TIMESTAMP(:ts, 'YYYY-MM-DD HH24:MI:SS')
    """)
    
    params = {"lid": "LINE_M_A", "ts": "2024-01-01 00:00:00"}
    iterations = 2000

    print(f"--- ORACLE BENCHMARK ({iterations} iterations) ---")

    with engine.connect() as conn:
        # 1. Warm up (optional connection overhead)
        conn.execute(text("SELECT 1 FROM dual"))

        # 2. Test WITH Index
        start = time.time()
        for _ in range(iterations):
            conn.execute(sql_with_index, params)
        end = time.time()
        time_index = end - start
        print(f"WITH Index:    {time_index:.4f} seconds")

        # 3. Test WITHOUT Index
        start = time.time()
        for _ in range(iterations):
            conn.execute(sql_no_index, params)
        end = time.time()
        time_no_index = end - start
        print(f"WITHOUT Index: {time_no_index:.4f} seconds")

    # Conclusion
    if time_no_index > 0:
        improvement = (time_no_index - time_index) / time_no_index * 100
        print(f"Improvement:   {improvement:.1f}% faster with index")

if __name__ == "__main__":
    run_benchmark()