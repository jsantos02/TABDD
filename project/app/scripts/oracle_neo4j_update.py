# app/scripts/oracle_neo4j_update.py

from collections import defaultdict

from sqlalchemy import text

from app.db.oracle import get_engine
from app.db.neo4j import get_driver


def load_from_oracle():
    """Load lines, stops and stop_times from Oracle as dicts."""
    engine = get_engine()
    with engine.begin() as conn:
        # active lines
        lines = conn.execute(
            text(
                """
                SELECT line_id, code, name, line_mode, active
                FROM lines
                WHERE active = 1
                """
            )
        ).mappings().all()

        # all stops
        stops = conn.execute(
            text(
                """
                SELECT stop_id, code, name, lat, lon
                FROM stops
                """
            )
        ).mappings().all()

        # stop_times ordered by line and time from start
        stop_times = conn.execute(
            text(
                """
                SELECT stop_time_id, line_id, stop_id, scheduled_seconds_from_start
                FROM stop_times
                ORDER BY line_id, scheduled_seconds_from_start
                """
            )
        ).mappings().all()

    return lines, stops, stop_times


def build_segments(stop_times):
    """
    From ordered stop_times, build NEXT segments:
    (from_stop_id, to_stop_id, seq, avg_travel_s) per line.
    """
    by_line = defaultdict(list)
    for row in stop_times:
        by_line[row["line_id"]].append(row)

    segments = []

    for line_id, lst in by_line.items():
        # already ordered by scheduled_seconds_from_start in SQL,
        # but sort again just to be safe
        lst_sorted = sorted(lst, key=lambda r: r["scheduled_seconds_from_start"])
        for idx in range(len(lst_sorted) - 1):
            current = lst_sorted[idx]
            nxt = lst_sorted[idx + 1]
            delta = nxt["scheduled_seconds_from_start"] - current["scheduled_seconds_from_start"]
            # fallback: if something weird, use at least 60s
            avg_travel_s = int(delta) if delta and delta > 0 else 60

            segments.append(
                {
                    "line_id": line_id,
                    "from_stop_id": current["stop_id"],
                    "to_stop_id": nxt["stop_id"],
                    "seq": idx + 1,
                    "avg_travel_s": avg_travel_s,
                }
            )

    return segments


def sync_to_neo4j(lines, stops, segments):
    """Write lines, stops and NEXT edges into Neo4j."""
    driver = get_driver()

    with driver.session() as session:
        # 1) (optional) wipe existing graph (careful if you reuse DB)
        session.run("MATCH (n) DETACH DELETE n")

        # 2) Constraints / indexes (as in your Part I report)
        session.run(
            """
            CREATE CONSTRAINT stop_id_unique IF NOT EXISTS
            FOR (s:Stop) REQUIRE s.stop_id IS UNIQUE
            """
        )
        session.run(
            """
            CREATE CONSTRAINT line_id_unique IF NOT EXISTS
            FOR (l:Line) REQUIRE l.line_id IS UNIQUE
            """
        )
        session.run(
            """
            CREATE INDEX stop_code IF NOT EXISTS
            FOR (s:Stop) ON (s.code)
            """
        )

        # 3) Load Stops
        session.run(
            """
            UNWIND $stops AS s
            MERGE (st:Stop { stop_id: s.stop_id })
            SET st.code = s.code,
                st.name = s.name,
                st.location = point({
                    longitude: coalesce(s.lon, 0.0),
                    latitude:  coalesce(s.lat, 0.0)
                })
            """,
            stops=[
                {
                    "stop_id": s["stop_id"],
                    "code": s["code"],
                    "name": s["name"],
                    "lat": float(s["lat"]) if s["lat"] is not None else None,
                    "lon": float(s["lon"]) if s["lon"] is not None else None,
                }
                for s in stops
            ],
        )

        # 4) Load Lines
        session.run(
            """
            UNWIND $lines AS l
            MERGE (ln:Line { line_id: l.line_id })
            SET ln.code   = l.code,
                ln.name   = l.name,
                ln.mode   = l.line_mode,
                ln.active = l.active
            """,
            lines=[
                {
                    "line_id": l["line_id"],
                    "code": l["code"],
                    "name": l["name"],
                    "mode": l["line_mode"],
                    "active": int(l["active"]),
                }
                for l in lines
            ],
        )

        # 5) NEXT + SERVES relationships
        session.run(
            """
            UNWIND $segments AS seg
            MATCH (a:Stop { stop_id: seg.from_stop_id })
            MATCH (b:Stop { stop_id: seg.to_stop_id })
            MATCH (ln:Line { line_id: seg.line_id })

            MERGE (a)-[r:NEXT { line_id: seg.line_id, seq: seg.seq }]->(b)
            SET r.avg_travel_s = seg.avg_travel_s

            MERGE (a)-[:SERVES]->(ln)
            MERGE (b)-[:SERVES]->(ln)
            """,
            segments=segments,
        )

    
        # 6) NEW: TRANSFER edges between nearby/identical stops
        transfer_pairs = [
            # Metro ↔ Bus at Aliados
            {"from_id": "M_STOP_ALIADOS",      "to_id": "B_STOP_ALIADOS",      "walk_s": 180},
            # Metro ↔ Bus at São Bento
            {"from_id": "M_STOP_SAO_BENTO",    "to_id": "B_STOP_SAO_BENTO",    "walk_s": 180},
            # Metro ↔ Bus at Jardim do Morro
            {"from_id": "M_STOP_JARDIM_MORRO", "to_id": "B_STOP_JARDIM_MORRO", "walk_s": 180},
            # Metro ↔ Bus at Santo Ovídio
            {"from_id": "M_STOP_SANTO_OVIDIO", "to_id": "B_STOP_SANTO_OVIDIO", "walk_s": 180},
            # Hospital / University area
            {"from_id": "M_STOP_HOSP_S_JOAO",  "to_id": "B_STOP_HOSP_S_JOAO",  "walk_s": 180},
            {"from_id": "M_STOP_POLO_UNIV",    "to_id": "B_STOP_POLO_UNIV",    "walk_s": 180},
            {"from_id": "M_STOP_MARQUES",      "to_id": "B_STOP_MARQUES",      "walk_s": 120},
            # Central hub at Trindade
            {"from_id": "M_STOP_TRINDADE",     "to_id": "B_STOP_TRINDADE",     "walk_s": 120},
        ]

        session.run(
            """
            UNWIND $pairs AS p
            MATCH (a:Stop { stop_id: p.from_id })
            MATCH (b:Stop { stop_id: p.to_id })

            // bidirectional TRANSFER edges with walking time
            MERGE (a)-[t1:TRANSFER]->(b)
            SET t1.walk_s = p.walk_s

            MERGE (b)-[t2:TRANSFER]->(a)
            SET t2.walk_s = p.walk_s
            """,
            pairs=transfer_pairs,
        )

        # (Optional) You can later add TRANSFER edges here, based on
        # shared locations / manual mapping between nearby stops.
        # For now, NEXT+SERVES is enough to power shortest-path routing.


def main():
    print("Loading data from Oracle...")
    lines, stops, stop_times = load_from_oracle()
    print(f"  Lines: {len(lines)}")
    print(f"  Stops: {len(stops)}")
    print(f"  Stop_times: {len(stop_times)}")

    print("Building segments for NEXT relationships...")
    segments = build_segments(stop_times)
    print(f"  Segments: {len(segments)}")

    print("Syncing to Neo4j...")
    sync_to_neo4j(lines, stops, segments)
    print("Done! Neo4j graph populated.")


if __name__ == "__main__":
    main()
