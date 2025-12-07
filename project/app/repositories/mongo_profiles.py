# project/app/repositories/mongo_profiles.py
from typing import Dict, Any
from app.db.mongo import mongo_db

def get_or_create_profile(user_id: str) -> Dict[str, Any]:
    profiles = mongo_db.user_profiles
    profile = profiles.find_one({"_id": user_id})
    
    if not profile:
        profile = {
            "_id": user_id,
            "favorites": {
                "lines": [],
                "stops": [],
            },
            "prefs": {
                "notifyDisruptions": True,
                "units": "metric",
            },
            "recentTrips": [],
        }
        profiles.insert_one(profile)
    return profile

def update_favorite_line(user_id: str, line_id: str, is_favorite: bool):
    profiles = mongo_db.user_profiles
    operation = "$addToSet" if is_favorite else "$pull"
    
    # Ensure doc exists
    profiles.update_one(
        {"_id": user_id},
        {
            "$setOnInsert": {"prefs": {"notifyDisruptions": True, "units": "metric"}},
            operation: {"favorites.lines": line_id}
        },
        upsert=True
    )

def update_favorite_stop(user_id: str, stop_id: str, is_favorite: bool):
    profiles = mongo_db.user_profiles
    operation = "$addToSet" if is_favorite else "$pull"
    
    profiles.update_one(
        {"_id": user_id},
        {
            "$setOnInsert": {"prefs": {"notifyDisruptions": True, "units": "metric"}},
            operation: {"favorites.stops": stop_id}
        },
        upsert=True
    )

def update_preferences(user_id: str, notify: bool, units: str):
    profiles = mongo_db.user_profiles
    profiles.update_one(
        {"_id": user_id},
        {
            "$set": {
                "prefs.notifyDisruptions": notify,
                "prefs.units": units,
            },
            "$setOnInsert": {
                "favorites": {"lines": [], "stops": []},
                "recentTrips": [],
            },
        },
        upsert=True
    )