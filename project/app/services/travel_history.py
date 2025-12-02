# app/services/travel_history.py
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import text
from app.db.oracle import get_engine
from app.db.mongo import mongo_db   # your existing mongo_db from mongo.py


def _new_id() -> str:
    return str(uuid.uuid4())


def create_trip_oracle(
    user_id: Optional[str],
    line_id: Optional[str],
    origin_stop_id: Optional[str],
    dest_stop_id: Optional[str],
    planned_start: datetime,
    planned_end: Optional[datetime],
    stops_sequence: Optional[List[Dict]] = None,
) -> str:
    """
    Insert into Oracle trips (+ trip_stops if provided) and return trip_id.
    stops_sequence: list of { "stop_id": ..., "eta": datetime | None, "ata": datetime | None }
    """
    trip_id = _new_id()

    with get_engine().begin() as conn:
        conn.execute(
            text("""
                INSERT INTO trips (
                    trip_id, user_id, line_id,
                    origin_stop_id, dest_stop_id,
                    planned_start, planned_end
                )
                VALUES (
                    :trip_id, :user_id, :line_id,
                    :origin_stop_id, :dest_stop_id,
                    :planned_start, :planned_end
                )
            """),
            {
                "trip_id": trip_id,
                "user_id": user_id,
                "line_id": line_id,
                "origin_stop_id": origin_stop_id,
                "dest_stop_id": dest_stop_id,
                "planned_start": planned_start,
                "planned_end": planned_end,
            },
        )

        if stops_sequence:
            for s in stops_sequence:
                conn.execute(
                    text("""
                        INSERT INTO trip_stops (
                            trip_id, stop_id, eta, ata
                        ) VALUES (
                            :trip_id, :stop_id, :eta, :ata
                        )
                    """),
                    {
                        "trip_id": trip_id,
                        "stop_id": s["stop_id"],
                        "eta": s.get("eta"),
                        "ata": s.get("ata"),
                    },
                )

    return trip_id


def mirror_trip_to_mongo(
    trip_id: str,
    user_id: Optional[str],
    line_id: Optional[str],
    origin_stop_id: Optional[str],
    dest_stop_id: Optional[str],
    planned_start: datetime,
    planned_end: Optional[datetime],
):
    """
    Mirror trip metadata into MongoDB:
      - trips collection
      - user_profiles.recentTrips
    """
    now = datetime.utcnow()

    trips_coll = mongo_db["trips"]
    profiles_coll = mongo_db["user_profiles"]

    # 1) Insert / upsert into trips collection
    trips_coll.replace_one(
        {"_id": trip_id},
        {
            "_id": trip_id,
            "user_id": user_id,
            "line_id": line_id,
            "origin_stop": origin_stop_id,
            "dest_stop": dest_stop_id,
            "planned_start": planned_start,
            "planned_end": planned_end,
            "created_at": now,
        },
        upsert=True,
    )

    # 2) Update user's recentTrips (document schema from your Part I)
    if user_id:
        profiles_coll.update_one(
            {"_id": user_id},
            {
                # ensure structure exists
                "$setOnInsert": {
                    "favorites": {"lines": [], "stops": []},
                    "prefs": {"notifyDisruptions": False, "units": "metric"},
                    "recentTrips": [],
                },
                # push new entry to the recentTrips array
                "$push": {
                    "recentTrips": {
                        "trip_id": trip_id,
                        "at": now,
                        "origin": origin_stop_id,
                        "dest": dest_stop_id,
                    }
                },
            },
            upsert=True,
        )


def create_trip_polyglot(
    user_id: Optional[str],
    line_id: Optional[str],
    origin_stop_id: Optional[str],
    dest_stop_id: Optional[str],
    planned_start: datetime,
    planned_end: Optional[datetime],
    stops_sequence: Optional[List[Dict]] = None,
) -> str:
    """
    High-level helper:
      1) write into Oracle (trips + trip_stops)
      2) mirror into Mongo (trips + user_profiles.recentTrips)
    """
    trip_id = create_trip_oracle(
        user_id=user_id,
        line_id=line_id,
        origin_stop_id=origin_stop_id,
        dest_stop_id=dest_stop_id,
        planned_start=planned_start,
        planned_end=planned_end,
        stops_sequence=stops_sequence,
    )

    mirror_trip_to_mongo(
        trip_id=trip_id,
        user_id=user_id,
        line_id=line_id,
        origin_stop_id=origin_stop_id,
        dest_stop_id=dest_stop_id,
        planned_start=planned_start,
        planned_end=planned_end,
    )

    return trip_id
