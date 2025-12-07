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