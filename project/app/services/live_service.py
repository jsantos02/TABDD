# project/app/services/live_service.py
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, List, Optional
import math

from app.repositories import mongo_vehicles, oracle_ops

def _interpolate(a: Tuple[float, float], b: Tuple[float, float], t: float) -> Tuple[float, float]:
    lon = a[0] + (b[0] - a[0]) * t
    lat = a[1] + (b[1] - a[1]) * t
    return lon, lat

def _advance_segment(itinerary, idx, segment_start, now):
    if not itinerary or len(itinerary) < 2:
        return 0, now, 0.0, 0

    if segment_start is None:
        segment_start = now

    # Normalize Timezones
    if segment_start.tzinfo is None and now.tzinfo is not None:
        segment_start = segment_start.replace(tzinfo=now.tzinfo)
    elif segment_start.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=segment_start.tzinfo)

    # Ensure index is within bounds
    idx = max(0, min(idx, len(itinerary) - 2))

    while True:
        travel_s = int(itinerary[idx].get("avgStopSec") or 300) 
        elapsed = (now - segment_start).total_seconds()

        # If still traversing this segment
        if elapsed < travel_s:
            return idx, segment_start, elapsed, travel_s

        # Move to next segment
        segment_start = segment_start + timedelta(seconds=travel_s)
        idx += 1

        # Loop around if at end
        if idx >= len(itinerary) - 1:
            idx = 0

def calculate_positions(line_id: str):
    # Fetch Data
    itinerary = mongo_vehicles.get_line_itinerary(line_id)
    if not itinerary or len(itinerary) < 2:
        return {"error": "Itinerary missing or too short"}

    stop_ids = [i["stop_id"] for i in itinerary]
    coords_map, meta_map = mongo_vehicles.get_stops_metadata(stop_ids)
    
    assignment_map = oracle_ops.get_active_assignments(line_id)
    active_vehicle_ids = list(assignment_map.keys())
    
    vehicles = mongo_vehicles.get_vehicles_by_ids(active_vehicle_ids, line_id)
    
    now = datetime.now(timezone.utc)
    enriched_vehicles = []

    if not active_vehicle_ids:
        note = "No active driver assignments now"
    else:
        note = None

    # Simulate vehicles
    for v in vehicles:
        sim = v.get("sim") or {}
        idx = int(sim.get("idx") or 0)
        seg_start = sim.get("segment_start_ts") or now

        # Calculate new position
        new_idx, new_seg_start, elapsed, travel_s = _advance_segment(itinerary, idx, seg_start, now)
        
        from_stop = itinerary[new_idx]["stop_id"]
        to_stop = itinerary[new_idx+1]["stop_id"]
        
        progress = 0.0
        loc_obj = None
        
        if from_stop in coords_map and to_stop in coords_map and travel_s > 0:
            progress = max(0.0, min(1.0, elapsed / travel_s))
            lon, lat = _interpolate(coords_map[from_stop], coords_map[to_stop], progress)
            loc_obj = {"type": "Point", "coordinates": [lon, lat]}

        # Update vehicle simulation state
        mongo_vehicles.update_vehicle_simulation(
            v["_id"], 
            {"idx": new_idx, "segment_start_ts": new_seg_start},
            loc_obj,
            now
        )

        remaining_s = max(int(travel_s - elapsed), 0)
        assign_info = assignment_map.get(str(v.get("_id")))
        
        payload = {
            "vehicle_id": v.get("_id"),
            "plate": v.get("plate"),
            "model": v.get("model"),
            "capacity": v.get("capacity"),
            "line_id": line_id,
            "lastKnown": {"ts": now.isoformat(), "loc": loc_obj} if loc_obj else None,
            "departed_stop": meta_map.get(from_stop),
            "next_stop": meta_map.get(to_stop),
            "eta_to_next_stop_s": remaining_s,
            "status": "active" if assign_info else "inactive"
        }
        
        if assign_info:
            payload.update(assign_info)
            
        enriched_vehicles.append(payload)

    return {
        "line_id": line_id,
        "ts": now.isoformat(),
        "vehicles": enriched_vehicles,
        "note": note
    }