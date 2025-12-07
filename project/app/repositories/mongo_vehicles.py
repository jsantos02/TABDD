# project/app/repositories/mongo_vehicles.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db.mongo import mongo_db

def get_line_itinerary(line_id: str) -> List[Dict]:
    doc = mongo_db.lines.find_one(
        {"_id": line_id}, 
        {"itinerary": 1, "mode": 1, "code": 1, "name": 1}
    )
    if not doc:
        return []
    itinerary = doc.get("itinerary") or []
    # Ensure sorted by sequence
    return sorted(itinerary, key=lambda x: x.get("seq", 0))

# gets coordinates for stops
def get_stops_metadata(stop_ids: List[str]):
    cursor = mongo_db.stops.find(
        {"_id": {"$in": stop_ids}},
        {"_id": 1, "code": 1, "name": 1, "location": 1}
    )
    
    coords_map = {}
    meta_map = {}
    
    for d in cursor:
        sid = d["_id"]
        meta_map[sid] = {"stop_id": sid, "code": d.get("code"), "name": d.get("name")}
        
        loc = d.get("location") or {}
        coords = loc.get("coordinates")
        if coords and len(coords) == 2:
            coords_map[sid] = (float(coords[0]), float(coords[1]))
            
    return coords_map, meta_map

def get_vehicles_by_ids(vehicle_ids: List[str], line_id: str) -> List[Dict]:
    
    query = {"line": line_id}
    if vehicle_ids:
        query["_id"] = {"$in": vehicle_ids}
    return list(mongo_db.vehicles.find(query))

def update_vehicle_simulation(vehicle_id: str, sim_data: Dict, location: Optional[Dict], now_ts: datetime):
    update = {
        "$set": {
            "sim.idx": sim_data["idx"],
            "sim.segment_start_ts": sim_data["segment_start_ts"]
        }
    }
    if location:
        update["$set"]["lastKnown"] = {
            "ts": now_ts,
            "loc": location
        }
        
    mongo_db.vehicles.update_one({"_id": vehicle_id}, update)