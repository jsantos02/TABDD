import math
from app.db.neo4j import get_driver
from app.db.mongo import mongo_db
from app.repositories import oracle_lines

def calculate_distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2): return 0.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(math.sqrt(a))

def find_best_route(origin_id: str, dest_id: str, units: str = "metric"):
    # 1. Neo4j Pathfinding
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (origin:Stop { stop_id: $oid }), (dest:Stop { stop_id: $did })
            MATCH p = allShortestPaths((origin)-[:NEXT|TRANSFER*..50]-(dest))
            WITH p, [r IN relationships(p) | CASE WHEN type(r)='TRANSFER' THEN 'TRANSFER' ELSE coalesce(r.line_id,'UNKNOWN') END] AS lids
            WITH p, reduce(sw=0, i IN range(1, size(lids)-1) | sw + CASE WHEN lids[i]<>lids[i-1] THEN 1 ELSE 0 END) AS switches
            ORDER BY switches ASC RETURN p AS path LIMIT 1
        """, oid=origin_id, did=dest_id).single()

    if not result:
        return None

    path = result["path"]
    nodes, rels = path.nodes, path.relationships
    
    segments, lines_used, stop_ids = [], set(), set()
    total_travel_s = 0

    # 2. Build Segments
    for i, rel in enumerate(rels):
        from_n, to_n = nodes[i], nodes[i+1]
        line_id = rel.get("line_id")
        
        if line_id: lines_used.add(line_id)
        stop_ids.add(from_n.get("stop_id"))
        stop_ids.add(to_n.get("stop_id"))
        
        # Extract individual components
        avg_travel = rel.get("avg_travel_s") or 0
        walk_time = rel.get("walk_s") or 0
        cost = avg_travel + walk_time
        total_travel_s += cost
        
        segments.append({
            "rel_type": rel.type,
            "line_id": "WALK" if rel.type == "TRANSFER" else line_id,
            "from_stop": dict(from_n),
            "to_stop": dict(to_n),
            "avg_travel_s": avg_travel,  # Restored field
            "walk_s": walk_time,         # Restored field
            "cost_s": cost
        })

    # 3. Enrich with Oracle Data
    o_lines = oracle_lines.get_lines_by_ids(list(lines_used))
    o_stops = oracle_lines.get_stops_by_ids(list(stop_ids))

    # 4. Calculate Distances
    total_dist_km = 0.0
    for seg in segments:
        f_stop = o_stops.get(seg["from_stop"]["stop_id"], {})
        t_stop = o_stops.get(seg["to_stop"]["stop_id"], {})
        
        # Merge coords back into segment
        seg["from_stop"].update(f_stop)
        seg["to_stop"].update(t_stop)
        
        dist = calculate_distance_km(f_stop.get("lat"), f_stop.get("lon"), t_stop.get("lat"), t_stop.get("lon"))
        seg["dist_km"] = dist
        total_dist_km += dist

    # 5. Enrich with Mongo Data
    mongo_docs = list(mongo_db.lines.find({"_id": {"$in": list(lines_used)}}))
    mongo_map = {d["_id"]: d for d in mongo_docs}
    
    lines_enriched = []
    for lid in lines_used:
        ol = o_lines.get(lid, {})
        ml = mongo_map.get(lid, {})
        lines_enriched.append({
            "line_id": lid,
            "code": ol.get("code") or ml.get("code"),
            "name": ol.get("name") or ml.get("name"),
            "mongo_alerts": ml.get("alerts", [])
        })

    total_dist = total_dist_km * 0.621371 if units == "imperial" else total_dist_km

    return {
        "origin_stop_id": origin_id, "dest_stop_id": dest_id,
        "total_hops": len(rels), "total_travel_s": total_travel_s,
        "total_distance": round(total_dist, 2), "distance_unit": "mi" if units == "imperial" else "km",
        "segments": segments, "lines_used": list(lines_used), "lines_enriched": lines_enriched
    }