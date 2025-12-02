# app/scripts/sync_oracle_to_mongo.py
from collections import defaultdict

from sqlalchemy import text

from app.db.oracle import get_engine
from app.db.mongo import mongo_db


def load_from_oracle():
    engine = get_engine()

    with engine.begin() as conn:
        # ✅ use line_mode in Oracle, alias to "mode" for Python
        lines = conn.execute(
            text(
                """
                SELECT
                    line_id,
                    code,
                    name,
                    line_mode,
                    active
                FROM lines
                WHERE active = 1
                """
            )
        ).mappings().all()

        stops = conn.execute(
            text(
                """
                SELECT
                    stop_id,
                    code,
                    name,
                    lat,
                    lon
                FROM stops
                """
            )
        ).mappings().all()

        stop_times = conn.execute(
            text(
                """
                SELECT
                    stop_time_id,
                    line_id,
                    stop_id,
                    scheduled_seconds_from_start
                FROM stop_times
                """
            )
        ).mappings().all()

    return lines, stops, stop_times

def sync_stops(stops, stop_times):
    """
    Create / update Mongo 'stops' collection:
      {
        _id: stop_id,
        code: string,
        name: string,
        location: { type: "Point", coordinates: [lon, lat] },
        amenities: []
      }
    """
    stops_coll = mongo_db.stops

    # Prefer the canonical stops table, but fall back to joined rows if needed.
    if stops:
        iterable = stops
    else:
        # if for some reason you only have stop_times+joined stops
        iterable = {
            (st["stop_id"], st["stop_code"], st["stop_name"], st["lat"], st["lon"])
            for st in stop_times
        }
        iterable = [
            {
                "stop_id": sid,
                "code": code,
                "name": name,
                "lat": lat,
                "lon": lon,
            }
            for sid, code, name, lat, lon in iterable
        ]

    for s in iterable:
        lat = float(s["lat"]) if s["lat"] is not None else 0.0
        lon = float(s["lon"]) if s["lon"] is not None else 0.0

        doc = {
            "_id": s["stop_id"],
            "code": s["code"],
            "name": s["name"],
            "location": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "amenities": [],
        }

        stops_coll.replace_one({"_id": s["stop_id"]}, doc, upsert=True)


def sync_lines(lines, stop_times):
    """
    Create / update Mongo 'lines' collection to match your Part I spec:
      {
        _id: line_id,
        code: string,
        name: string,
        line_mode: "bus" | "tram" | "metro",
        itinerary: [
          { stop_id, seq, avgStopSec }
        ],
        alerts: []
      }
    """
    lines_coll = mongo_db.lines

    # Group stop_times per line
    grouped = defaultdict(list)
    for st in stop_times:
        grouped[st["line_id"]].append(st)

    for line in lines:
        line_id = line["line_id"]

        # sort again just in case
        stops_for_line = sorted(
            grouped.get(line_id, []),
            key=lambda r: r["scheduled_seconds_from_start"],
        )

        itinerary = []
        prev_sec = None
        seq = 1

        for st in stops_for_line:
            sec = int(st["scheduled_seconds_from_start"])
            avg_stop_sec = 0 if prev_sec is None else sec - prev_sec

            itinerary.append(
                {
                    "stop_id": st["stop_id"],
                    "seq": seq,
                    "avgStopSec": avg_stop_sec,
                }
            )
            prev_sec = sec
            seq += 1

        doc = {
            "_id": line_id,
            "code": line["code"],
            "name": line["name"],
            "mode": line["line_mode"],
            "itinerary": itinerary,
            "alerts": [],
        }

        lines_coll.replace_one({"_id": line_id}, doc, upsert=True)


def main():
    print("Loading data from Oracle...")
    lines, stops, stop_times = load_from_oracle()
    print(f"Loaded {len(lines)} lines, {len(stops)} stops, {len(stop_times)} stop_times")

    print("Syncing stops into MongoDB...")
    sync_stops(stops, stop_times)

    print("Syncing lines into MongoDB...")
    sync_lines(lines, stop_times)

    print("Done.")


if __name__ == "__main__":
    main()
