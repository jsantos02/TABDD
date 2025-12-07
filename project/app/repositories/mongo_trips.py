# project/app/repositories/mongo_trips.py
from typing import List, Dict, Any
from datetime import datetime
from app.db.mongo import mongo_db

# Insert a new trip document into MongoDB
def create_trip(data: Dict[str, Any]):
    trips_col = mongo_db["trips"]
    trips_col.insert_one(data)

# Updates the user's profile with the new trip.
def add_trip_to_user_history(user_id: str, trip_summary: Dict[str, Any]):
    profiles = mongo_db["user_profiles"]
    profiles.update_one(
        {"_id": user_id},
        {
            "$setOnInsert": {
                "favorites": {"lines": [], "stops": []},
                "prefs": {},   
            },
            "$push": {
                "recentTrips": {
                    "$each": [trip_summary],
                    "$slice": -10,  # keep last 10
                }
            },
        },
        upsert=True,
    )

def get_trip_details_by_ids(trip_ids: List[str]) -> Dict[str, Dict]:

    if not trip_ids:
        return {}
        
    cursor = mongo_db["trips"].find(
        {"_id": {"$in": trip_ids}},
        {"_id": 1, "lines_used": 1, "total_distance": 1, "distance_unit": 1},
    )
    
    return {doc["_id"]: doc for doc in cursor}