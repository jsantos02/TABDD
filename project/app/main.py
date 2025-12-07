from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Request,
    Form,
    status,
)
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
import uuid
from typing import Optional, List, Dict, Any, Tuple 
from app.db.oracle import get_engine
from app.db.redis import redis_client
from app.config import settings
from app.repositories import oracle_users, oracle_sessions
from datetime import datetime, timedelta, timezone
from app.db.mongo import mongo_db
from app.db.neo4j import get_driver
import math



app = FastAPI(title="Porto Transport App")
templates = Jinja2Templates(directory="app/templates")


# ##############################
# Pydantic models for JSON APIs
# ##############################

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TripSegment(BaseModel):
    stop_id: str
    eta: Optional[datetime] = None
    ata: Optional[datetime] = None


class TripCreate(BaseModel):
    origin_stop_id: str
    dest_stop_id: str
    line_id: Optional[str] = None
    planned_start: datetime
    planned_end: Optional[datetime] = None
    lines_used: Optional[List[str]] = None
    total_distance: float = 0.0
    distance_unit: str = "metric"

class LineFavoritePayload(BaseModel):
    line_id: str
    favorite: bool


class StopFavoritePayload(BaseModel):
    stop_id: str
    favorite: bool

class PrefsPayload(BaseModel):
    notifyDisruptions: bool = True
    units: str = "metric"  # "metric" | "imperial"

class FeedbackCreate(BaseModel):
    usability_rating: int  
    satisfaction_rating: int  
    comments: Optional[str] = None

# ##############################
# Helper functions
# ##############################

SESSION_PREFIX = "session:"


def create_session(user_id: str, request: Request) -> str:

    token = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=settings.SESSION_TTL_SECONDS)

    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None

    # Persists the session in Oracle DB
    oracle_sessions.create_user_session(
        session_id=token,
        user_id=user_id,
        issued_at=now,
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
    )

    # Persists the session in Redis cache
    redis_client.setex(
        SESSION_PREFIX + token,
        settings.SESSION_TTL_SECONDS,
        user_id,
    )

    return token


def get_user_id_from_token(token: str | None) -> str | None:
    if not token:
        return None

    # Returns user_id if valid session
    user_id = redis_client.get(SESSION_PREFIX + token)
    if user_id:
        return user_id

    # Returns None if not in Redis - check Oracle
    session = oracle_sessions.get_active_session(token)
    if not session:
        return None  # no session in Oracle either

    user_id = session["user_id"]

   
    expires_at = session["expires_at"]
    # Expires the session in 1 hour. (in the future it would be nice to have it not expire if active)
    now = datetime.now(datetime.timezone.utc)
    ttl_seconds = int((expires_at - now).total_seconds())

    if ttl_seconds > 0:
        redis_client.setex(SESSION_PREFIX + token, ttl_seconds, user_id)

    return user_id


async def get_current_user(request: Request):
    
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")

    user = oracle_users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user

# Create user profile in MongoDB if not exists
def ensure_mongo_profile(db, user_id: str):
    profiles = db.user_profiles
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

# Helper to get active alerts for a user
def get_active_user_alerts(user_id: str):
    alerts = []
    profile = mongo_db.user_profiles.find_one({"_id": user_id})
    
    if profile and profile.get("prefs", {}).get("notifyDisruptions", True):
        fav_line_ids = profile.get("favorites", {}).get("lines", [])
        
        if fav_line_ids:
            lines_with_alerts = mongo_db.lines.find({
                "_id": {"$in": fav_line_ids},
                "alerts": {"$not": {"$size": 0}} 
            })

            now = datetime.now(timezone.utc)

            for line in lines_with_alerts:
                for alert in line.get("alerts", []):
                    start_dt = alert.get("from")
                    end_dt = alert.get("to")
                    
                    if start_dt and start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    if end_dt and end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)

                    if start_dt and start_dt <= now:
                        if not end_dt or end_dt > now:
                            alerts.append({
                                "line_code": line.get("code"),
                                "line_name": line.get("name"),
                                "msg": alert.get("msg"),
                                "level": "warning"
                            })
    return alerts

def calculate_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return 0.0
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    # Harversine formula
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # radius of earth in kilometers
    return c * r
# ##############################
# HTML pages for login and registration
# ##############################

# Home page redirects to login if user not logged in. Also alerts when favorite lines have disruptions will be done here to fullfill requirements
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    token = request.cookies.get("session_token")
    user = None
    alerts = []

    if token:
        user_id = get_user_id_from_token(token)
        if user_id:
            user = oracle_users.get_user_by_id(user_id)
            # Use the helper here
            alerts = get_active_user_alerts(user_id)

    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user, "alerts": alerts},
    )

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )

# Login form submission
@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    """
    Handles the HTML login form (login.html).
    """
    user = oracle_users.get_user_by_email(email)
    if not user or not oracle_users.verify_password(password, user["password_hash"]):
        # Re-render login page with error
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=400,
        )

    token = create_session(user["user_id"], request)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=settings.SESSION_TTL_SECONDS,
    )
    return response


# Register page
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": None},
    )

# Register submission
@app.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    # Check if user already exists, if not add it to oracle.
    existing = oracle_users.get_user_by_email(email)
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Email already registered"},
            status_code=400,
        )

    user_id = oracle_users.create_user(
        email=email,
        password=password,
        full_name=full_name,
    )

    # create session and redirect to home after registering
    token = create_session(user_id, request)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=settings.SESSION_TTL_SECONDS,
    )
    return response


@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")

    if token:
        # remove session from Redis.
        redis_client.delete(SESSION_PREFIX + token)
        # remove session from Oracle.
        oracle_sessions.delete_user_session(token)

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


# to verify session and get current user info
@app.get("/me")
def me(current_user=Depends(get_current_user)):
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "is_active": current_user["is_active"],
    }
# ##############################
# API endpoints
# ##############################

# Show alerts API for current user
@app.get("/api/alerts")
def api_alerts(current_user=Depends(get_current_user)):
    return get_active_user_alerts(current_user["user_id"])

@app.post("/api/auth/register")
def api_register(data: RegisterRequest):
    existing = oracle_users.get_user_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = oracle_users.create_user(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
    )

    return {"user_id": user_id}


@app.post("/api/auth/login")
def api_login(request: Request, data: LoginRequest):
    user = oracle_users.get_user_by_email(data.email)
    if not user or not oracle_users.verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_session(user["user_id"], request)

    response = JSONResponse({"access_token": token, "token_type": "bearer"})
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=settings.SESSION_TTL_SECONDS,
    )
    return response




# find line in mongodb
@app.get("/api/lines/{line_id}")
def line_detail(line_id: str, _=Depends(get_current_user)):

    doc = mongo_db.lines.find_one({"_id": line_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Line not found in MongoDB")
    
    doc["_id"] = str(doc["_id"])

    return doc

# fallback oracle line detail
@app.get("/api/oracle/lines/{line_id}")
def oracle_line_detail(line_id: str, current_user=Depends(get_current_user)):
    with get_engine().begin() as conn:
        # Fetch line info
        line_row = conn.execute(
            text("SELECT line_id, code, name, line_mode, active FROM lines WHERE line_id = :lid"),
            {"lid": line_id}
        ).mappings().first()

        if not line_row:
            raise HTTPException(status_code=404, detail="Line not found")

        # Fetch stops
        stops_rows = conn.execute(
            text("""
                SELECT s.stop_id, s.code, s.name, st.scheduled_seconds_from_start
                FROM stop_times st
                JOIN stops s ON s.stop_id = st.stop_id
                WHERE st.line_id = :lid
                ORDER BY st.scheduled_seconds_from_start
            """),
            {"lid": line_id}
        ).mappings().all()

        # Fetch Schedules 
        schedules_rows = conn.execute(
            text("""
                SELECT 
                    dow, 
                    TO_CHAR(start_time, 'HH24:MI') as start_str, 
                    TO_CHAR(end_time, 'HH24:MI') as end_str, 
                    headway_minutes
                FROM line_schedules
                WHERE line_id = :lid
                ORDER BY dow
            """),
            {"lid": line_id}
        ).mappings().all()

    return {
        "line": dict(line_row),
        "stops": [dict(r) for r in stops_rows],
        "schedules": [dict(r) for r in schedules_rows] 
    }

# create trip 
@app.post("/api/trips")
def create_trip(trip: TripCreate, current_user=Depends(get_current_user),):
    user_id = current_user["user_id"]
    now = datetime.now(timezone.utc)
    trip_id = str(uuid.uuid4())

    # Decide what goes into lines_used for Mongo
    if trip.lines_used and len(trip.lines_used) > 0:
        lines_used = trip.lines_used
    elif trip.line_id:
        lines_used = [trip.line_id]
    else:
        lines_used = []

    # oracle version
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                INSERT INTO trips (
                  trip_id, user_id, line_id,
                  origin_stop_id, dest_stop_id,
                  planned_start, planned_end, created_at
                ) VALUES (
                  :trip_id, :user_id, :line_id,
                  :origin_stop_id, :dest_stop_id,
                  :planned_start, :planned_end, :created_at
                )
            """),
            {
                "trip_id": trip_id,
                "user_id": user_id,
                "line_id": trip.line_id,
                "origin_stop_id": trip.origin_stop_id,
                "dest_stop_id": trip.dest_stop_id,
                "planned_start": trip.planned_start,
                "planned_end": trip.planned_end,
                "created_at": now,
            },
        )
    
    # mongo version
    trips_col = mongo_db["trips"]
    trips_col.insert_one(
        {
            "_id": trip_id,
            "user_id": user_id,
            "line_id": trip.line_id,
            "lines_used": lines_used,  # full list of lines for history
            "origin_stop": trip.origin_stop_id,
            "dest_stop": trip.dest_stop_id,
            "planned_start": trip.planned_start,
            "planned_end": trip.planned_end,
            "created_at": now,
            "total_distance": trip.total_distance,
            "distance_unit": trip.distance_unit,
        }
    )

    # update user profile recentTrips
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
                    "$each": [
                        {
                            "trip_id": trip_id,
                            "at": now,
                            "origin": trip.origin_stop_id,
                            "dest": trip.dest_stop_id,
                            "lines": lines_used,
                            "dist": trip.total_distance, 
                            "unit": trip.distance_unit
                        }
                    ],
                    "$slice": -10,  # keep last 10
                }
            },
        },
        upsert=True,
    )

    return {"ok": True, "trip_id": trip_id, "user_id": user_id}


@app.get("/api/route")
def get_route(origin_stop_id: str,dest_stop_id: str,current_user=Depends(get_current_user),):
    driver = get_driver()
    # neo4j shortest path query
    with driver.session() as session:
        result = session.run(
            """
            MATCH (origin:Stop { stop_id: $origin_id }),
                (dest:Stop   { stop_id: $dest_id })

            MATCH p = allShortestPaths(
            (origin)-[:NEXT|TRANSFER*..50]-(dest)
            )

            WITH p,
                [r IN relationships(p) |
                    CASE
                    WHEN type(r) = 'TRANSFER' THEN 'TRANSFER'
                    ELSE coalesce(r.line_id, 'UNKNOWN')
                    END
                ] AS lids

            WITH p,
                reduce(sw = 0, i IN range(1, size(lids)-1) |
                    sw + CASE WHEN lids[i] <> lids[i-1] THEN 1 ELSE 0 END
                ) AS switches

            ORDER BY switches ASC
            RETURN p AS path
            LIMIT 1
            """,
            origin_id=origin_stop_id,
            dest_id=dest_stop_id,
        )       

        record = result.single()

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="No route found between those stops"
            )

        path = record["path"]
        nodes = list(path.nodes)
        rels = list(path.relationships)

    segments = []
    total_travel_s = 0
    lines_used = []
    stop_ids = set()

    # Build segments from path
    for idx, rel in enumerate(rels):
        from_node = nodes[idx]
        to_node = nodes[idx + 1]

        rel_type = rel.type  # "NEXT" or "TRANSFER"

        if hasattr(rel, "get"):
            avg_travel_s = rel.get("avg_travel_s", 0)
            walk_s = rel.get("walk_s", 0)
            line_id = rel.get("line_id")
        else:
            avg_travel_s = rel["avg_travel_s"] if "avg_travel_s" in rel else 0
            walk_s = rel["walk_s"] if "walk_s" in rel else 0
            line_id = rel["line_id"] if "line_id" in rel else None

        cost = (avg_travel_s or 0) + (walk_s or 0)
        total_travel_s += cost

        if line_id and line_id not in lines_used:
            lines_used.append(line_id)

        if walk_s and rel_type == "TRANSFER":
            line_id = "WALK TO TRANSFER"

        from_stop_id = from_node.get("stop_id")
        to_stop_id = to_node.get("stop_id")

        if from_stop_id:
            stop_ids.add(from_stop_id)
        if to_stop_id:
            stop_ids.add(to_stop_id)

        segments.append(
            {
                "rel_type": rel_type,
                "from_stop": {
                    "stop_id": from_stop_id,
                    "code": from_node.get("code"),
                    "name": from_node.get("name"),
                },
                "to_stop": {
                    "stop_id": to_stop_id,
                    "code": to_node.get("code"),
                    "name": to_node.get("name"),
                },
                "line_id": line_id,
                "avg_travel_s": avg_travel_s,
                "walk_s": walk_s,
                "cost_s": cost,
            }
        )

    # Oracle fetch for lines and stops details
    oracle_lines = {}
    oracle_stops = {}

    engine = get_engine()
    with engine.connect() as conn:
        # Lines
        if lines_used:
            placeholders = ", ".join(
                f":line_id_{i}" for i in range(len(lines_used))
            )
            params = {f"line_id_{i}": lid for i, lid in enumerate(lines_used)}

            line_rows = conn.execute(
                text(
                    f"""
                    SELECT line_id, code, name, line_mode
                    FROM lines
                    WHERE line_id IN ({placeholders})
                    """
                ),
                params,
            ).mappings().all()

            for r in line_rows:
                oracle_lines[r["line_id"]] = {
                    "line_id": r["line_id"],
                    "code": r["code"],
                    "name": r["name"],
                    "mode": r["line_mode"],  # normalized key for API
                }

        # Stops
        if stop_ids:
            stop_ids_list = list(stop_ids)
            placeholders = ", ".join(
                f":stop_id_{i}" for i in range(len(stop_ids_list))
            )
            params = {f"stop_id_{i}": sid for i, sid in enumerate(stop_ids_list)}

            stop_rows = conn.execute(
                text(
                    f"""
                    SELECT stop_id, code, name, lat, lon
                    FROM stops
                    WHERE stop_id IN ({placeholders})
                    """
                ),
                params,
            ).mappings().all()

            for r in stop_rows:
                oracle_stops[r["stop_id"]] = {
                    "stop_id": r["stop_id"],
                    "code": r["code"],
                    "name": r["name"],
                    "lat": float(r["lat"]) if r["lat"] is not None else None,
                    "lon": float(r["lon"]) if r["lon"] is not None else None,
                }

    # Attach coordinates and calculate distances
    # Fetch User Preference for Units
    profile = ensure_mongo_profile(mongo_db, current_user["user_id"])
    units_pref = profile.get("prefs", {}).get("units", "metric") # "metric" or "imperial"
    
    total_dist_km = 0.0

    for seg in segments:
        fsid = seg["from_stop"]["stop_id"]
        tsid = seg["to_stop"]["stop_id"]

        # Attach coordinates from Oracle 
        if fsid in oracle_stops:
            seg["from_stop"]["lat"] = oracle_stops[fsid]["lat"]
            seg["from_stop"]["lon"] = oracle_stops[fsid]["lon"]

        if tsid in oracle_stops:
            seg["to_stop"]["lat"] = oracle_stops[tsid]["lat"]
            seg["to_stop"]["lon"] = oracle_stops[tsid]["lon"]

        # Calculate segment distance
        flat = seg["from_stop"].get("lat")
        flon = seg["from_stop"].get("lon")
        tlat = seg["to_stop"].get("lat")
        tlon = seg["to_stop"].get("lon")
        
        dist = calculate_distance(flat, flon, tlat, tlon)
        seg["dist_km"] = dist
        total_dist_km += dist

    # Apply Unit Conversion
    if units_pref == "imperial":
        total_distance = total_dist_km * 0.621371
        unit_label = "mi"
    else:
        total_distance = total_dist_km
        unit_label = "km"


    # MongoDB import for line enrichment
    lines_coll = mongo_db["lines"]

    mongo_docs = list(
        lines_coll.find(
            {
                "$or": [
                    {"line_id": {"$in": lines_used}},
                    {"_id": {"$in": lines_used}},
                ]
            }
        )
    )

    mongo_by_line_id = {}
    for doc in mongo_docs:
        lid = doc.get("line_id") or doc.get("_id")
        if isinstance(lid, str):
            mongo_by_line_id[lid] = doc

    lines_enriched = []
    for lid in lines_used:
        o = oracle_lines.get(lid)
        m = mongo_by_line_id.get(lid, {})

        lines_enriched.append(
            {
                "line_id": lid,
                "code": (o or {}).get("code") or m.get("code"),
                "name": (o or {}).get("name") or m.get("name"),
                "mode": (o or {}).get("mode") or m.get("mode"),
                "from_oracle": bool(o),
                "from_mongo": bool(m),
                "mongo": {
                    "alerts": m.get("alerts", []),
                    "schedules": m.get("schedules"),
                },
            }
        )

    return {
        "origin_stop_id": origin_stop_id,
        "dest_stop_id": dest_stop_id,
        "total_hops": len(rels),
        "total_travel_s": total_travel_s,
        
        
        "total_distance": round(total_distance, 2),
        "distance_unit": unit_label,
        
        "lines_used": lines_used,
        "segments": segments,
        "lines_enriched": lines_enriched,
    }
# Get stops
@app.get("/api/stops")
def list_stops(_=Depends(get_current_user)):
    with get_engine().begin() as conn:
        result = conn.execute(
            text(
                """
                SELECT
                    stop_id,
                    code,
                    name,
                    lat,
                    lon
                FROM stops
                ORDER BY name
                """
            )
        )
        stops = [
            {
                "stop_id": row.stop_id,
                "code": row.code,
                "name": row.name,
                "lat": float(row.lat) if row.lat is not None else None,
                "lon": float(row.lon) if row.lon is not None else None,
            }
            for row in result
        ]

    return stops

# Let user set favorite lines
@app.post("/api/profile/favorites/lines")
def set_line_favorite(payload: LineFavoritePayload,current_user=Depends(get_current_user),):
    
    profiles = mongo_db.user_profiles
    update_doc = {}

    # Give default prefs on new profile
    update_doc["$setOnInsert"] = {
        "prefs": {"notifyDisruptions": True, "units": "metric"},
    }

    if payload.favorite:
        update_doc["$addToSet"] = {"favorites.lines": payload.line_id}
    else:
        update_doc["$pull"] = {"favorites.lines": payload.line_id}

    profiles.update_one(
        {"_id": current_user["user_id"]},
        update_doc,
        upsert=True,
    )

    return {"ok": True}

# favorite stops
@app.post("/api/profile/favorites/stops")
def set_stop_favorite(payload: StopFavoritePayload,current_user=Depends(get_current_user),):
    
    profiles = mongo_db.user_profiles

    update_doc = {}

    update_doc["$setOnInsert"] = {
        "prefs": {"notifyDisruptions": True, "units": "metric"},
    }

    if payload.favorite:
        update_doc["$addToSet"] = {"favorites.stops": payload.stop_id}
    else:
        update_doc["$pull"] = {"favorites.stops": payload.stop_id}

    profiles.update_one(
        {"_id": current_user["user_id"]},
        update_doc,
        upsert=True,
    )

    return {"ok": True}

@app.post("/api/profile/prefs")
def set_prefs(payload: PrefsPayload,current_user=Depends(get_current_user),):
   
    profiles = mongo_db.user_profiles

    profiles.update_one(
        {"_id": current_user["user_id"]},
        {
            "$set": {
                "prefs.notifyDisruptions": payload.notifyDisruptions,
                "prefs.units": payload.units,
            },
            "$setOnInsert": {
                "favorites": {"lines": [], "stops": []},
                "recentTrips": [],
            },
        },
        upsert=True,
    )

    return {"ok": True}


# ######################
# Live vehicles (Mongo)
# ######################

vehicles_col = mongo_db["vehicles"]
lines_col = mongo_db["lines"]
stops_col = mongo_db["stops"]

def _oracle_table_has_column(table_name: str, column_name: str) -> bool:
    sql = text("""
        SELECT COUNT(*) AS c
        FROM user_tab_columns
        WHERE table_name = :t
          AND column_name = :c
    """)
    with get_engine().begin() as conn:
        c = conn.execute(
            sql,
            {"t": table_name.upper(), "c": column_name.upper()}
        ).scalar()
    return int(c or 0) > 0


def _active_assignments_for_line(line_id: str) -> dict:
    has_end = _oracle_table_has_column("DRIVER_ASSIGNMENTS", "END_TS")

    now = datetime.now(timezone.utc)

    if has_end:
        sql = text("""
            SELECT assignment_id, vehicle_id, driver_id
            FROM driver_assignments
            WHERE line_id = :line_id
              AND start_ts <= :now
              AND (end_ts IS NULL OR end_ts > :now)
        """)
        params = {"line_id": line_id, "now": now}

    with get_engine().begin() as conn:
        rows = conn.execute(sql, params).fetchall()

    out = {}
    for r in rows:
        m = r._mapping
        vehicle_id = str(m["vehicle_id"])
        out[vehicle_id] = {
            "assignment_id": str(m["assignment_id"]),
            "driver_id": str(m["driver_id"]),
        }
    return out



def _load_itinerary(line_id: str) -> List[Dict[str, Any]]:
    line_doc = lines_col.find_one({"_id": line_id}, {"itinerary": 1, "mode": 1, "code": 1, "name": 1})
    if not line_doc:
        return []
    itinerary = line_doc.get("itinerary") or []
    itinerary = sorted(itinerary, key=lambda x: x.get("seq", 0))
    return itinerary


def _load_stop_meta(stop_ids: List[str]) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, Dict[str, Any]]]:
    """
    Returns:
      coords_map: stop_id -> (lon, lat)
      meta_map: stop_id -> {stop_id, code, name}
    """
    coords_map: Dict[str, Tuple[float, float]] = {}
    meta_map: Dict[str, Dict[str, Any]] = {}

    cursor = stops_col.find(
        {"_id": {"$in": stop_ids}},
        {"_id": 1, "code": 1, "name": 1, "location": 1},
    )

    for d in cursor:
        sid = d["_id"]
        meta_map[sid] = {"stop_id": sid, "code": d.get("code"), "name": d.get("name")}

        loc = (d.get("location") or {})
        coords = loc.get("coordinates")
        if isinstance(coords, list) and len(coords) == 2:
            try:
                lon, lat = float(coords[0]), float(coords[1])
                coords_map[sid] = (lon, lat)
            except Exception:
                pass

    return coords_map, meta_map


def _advance_segment(itinerary, idx, segment_start, now):
    if not itinerary or len(itinerary) < 2:
        return 0, now, 0.0, 0

    if segment_start is None:
        segment_start = now

    # Normalize tz-awareness if needed
    if isinstance(segment_start, datetime) and isinstance(now, datetime):
        if segment_start.tzinfo is None and now.tzinfo is not None:
            segment_start = segment_start.replace(tzinfo=now.tzinfo)
        elif segment_start.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=segment_start.tzinfo)

    idx = max(0, min(idx, len(itinerary) - 2))

    while True:
        travel_s = int(itinerary[idx].get("avgStopSec") or 300)
        elapsed = (now - segment_start).total_seconds()

        if elapsed < travel_s:
            return idx, segment_start, elapsed, travel_s

        segment_start = segment_start + timedelta(seconds=travel_s)
        idx += 1

        if idx >= len(itinerary) - 1:
            idx = 0


# normalize lon/lat data
def _interpolate(a: Tuple[float, float], b: Tuple[float, float], t: float) -> Tuple[float, float]:
    lon = a[0] + (b[0] - a[0]) * t
    lat = a[1] + (b[1] - a[1]) * t
    return lon, lat


def _simulate_vehicle_position(vehicle, itinerary, coords_map, meta_map, now, assignment=None):
    if len(itinerary) < 2:
        return {
            "vehicle_id": vehicle.get("_id"),
            "plate": vehicle.get("plate"),
            "line_id": vehicle.get("line"),
            "error": "Line itinerary too short to simulate",
        }

    sim = vehicle.get("sim") or {}
    idx = int(sim.get("idx") or 0)
    segment_start_ts = sim.get("segment_start_ts") or now  

    # Normalize tz-awareness if needed
    if isinstance(segment_start_ts, datetime):
        if segment_start_ts.tzinfo is None and now.tzinfo is not None:
            segment_start_ts = segment_start_ts.replace(tzinfo=now.tzinfo)

    idx, segment_start_ts, elapsed, travel_s = _advance_segment(
        itinerary, idx, segment_start_ts, now
    )

    from_stop_id = itinerary[idx]["stop_id"]
    to_stop_id = itinerary[idx + 1]["stop_id"]

    from_coords = coords_map.get(from_stop_id)
    to_coords = coords_map.get(to_stop_id)

    progress = 0.0
    loc_obj: Optional[Dict[str, Any]] = None

    if from_coords and to_coords and travel_s > 0:
        progress = max(0.0, min(1.0, float(elapsed) / float(travel_s)))
        lon, lat = _interpolate(from_coords, to_coords, progress)
        loc_obj = {"type": "Point", "coordinates": [lon, lat]}

    remaining_s = max(int(travel_s - elapsed), 0)

    # Write back a realistic lastKnown + sim state
    update_doc = {
        "$set": {
            "sim.idx": idx,
            "sim.segment_start_ts": segment_start_ts,
        }
    }

    if loc_obj:
        update_doc["$set"]["lastKnown"] = {
            "ts": now,
            "loc": loc_obj,
        }

    vehicles_col.update_one({"_id": vehicle["_id"]}, update_doc)

    payload = {
        "idx": idx,
        "segment_start_ts": segment_start_ts,
        "vehicle_id": vehicle.get("_id"),
        "plate": vehicle.get("plate"),
        "model": vehicle.get("model"),
        "capacity": vehicle.get("capacity"),
        "line_id": vehicle.get("line"),
        "lastKnown": {
            "ts": now.isoformat(),
            "loc": loc_obj,
        } if loc_obj else None,
        "departed_stop": meta_map.get(from_stop_id, {"stop_id": from_stop_id}),
        "next_stop": meta_map.get(to_stop_id, {"stop_id": to_stop_id}),
        "eta_next_s": remaining_s,
        "eta_to_next_stop_s": remaining_s,
        "eta_to_next_stop_min": int(math.ceil(remaining_s / 60)) if remaining_s is not None else None,
        "segment_progress": progress,
        "rel_type": "NEXT",
        "avg_travel_s": travel_s,
    }


    if assignment:
        payload["assignment_id"] = assignment.get("assignment_id")
        payload["driver_id"] = assignment.get("driver_id")
        payload["status"] = "active"
    else:
        payload["status"] = "inactive"

    return payload



@app.get("/api/live/{line_id}")
def live_line(line_id: str, _=Depends(get_current_user)):
    # Load line itinerary from Mongo
    itinerary = _load_itinerary(line_id)
    if not itinerary or len(itinerary) < 2:
        raise HTTPException(status_code=404, detail="Line not found in Mongo or itinerary too short")

    stop_ids = [i["stop_id"] for i in itinerary]
    coords_map, meta_map = _load_stop_meta(stop_ids)

    # Oracle decides who is active NOW
    assignment_map = _active_assignments_for_line(line_id)
    active_vehicle_ids = list(assignment_map.keys())

    # Get only active vehicles from Mongo
    mongo_query = {"line": line_id}
    if active_vehicle_ids:
        mongo_query["_id"] = {"$in": active_vehicle_ids}

    vehicles = list(vehicles_col.find(mongo_query))


    if not active_vehicle_ids:
        return {"line_id": line_id, "vehicles": [], "note": "No active driver assignments now"}

    now = datetime.now(timezone.utc)

    enriched = [
        _simulate_vehicle_position(
            v,
            itinerary,
            coords_map,
            meta_map,
            now,
            assignment=assignment_map.get(str(v.get("_id"))),
        )
        for v in vehicles
    ]

    return {
        "line_id": line_id,
        "ts": now.isoformat(),
        "active_assignments": assignment_map,
        "vehicles": enriched,
    }


# ################################
# Other HTML endpoints
# ################################
 

@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request):
    return templates.TemplateResponse(
        "feedback.html",
        {"request": request},
    )

@app.post("/feedback", response_class=HTMLResponse)
async def submit_feedback(request: Request,usability_rating: int = Form(...),satisfaction_rating: int = Form(...),comments: str = Form(""),current_user=Depends(get_current_user), ):
    feedback_data = {
        "user_id": current_user["user_id"], 
        "usability_rating": usability_rating,
        "satisfaction_rating": satisfaction_rating,
        "comments": comments,
        "submitted_at": datetime.now(timezone.utc),
    }

    # Insert into a new 'feedback' collection in MongoDB
    mongo_db.feedback.insert_one(feedback_data)

    return templates.TemplateResponse(
        "feedback.html",
        {
            "request": request,
            "msg": "Thank you for your feedback!"
        },
    )

@app.get("/lines", response_class=HTMLResponse)
async def lines_page(request: Request):

    token = request.cookies.get("session_token")
    user = None

    if token:
        user_id = get_user_id_from_token(token)
        if user_id:
            user = oracle_users.get_user_by_id(user_id)

    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Load all lines from Oracle
    with get_engine().begin() as conn:
        result = conn.execute(
            text(
                """
                SELECT
                    line_id,
                    code,
                    name,
                    line_mode,
                    active
                FROM lines
                ORDER BY code
                """
            )
        )
        lines = [dict(row._mapping) for row in result]

    return templates.TemplateResponse(
        "lines.html",
        {
            "request": request,
            "user": user,
            "lines": lines,
        },
    )

@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = current_user["user_id"]

    # Oracle fetch base trip info
    with get_engine().begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    t.trip_id,
                    t.planned_start,
                    t.planned_end,
                    t.line_id,
                    o.name AS origin_name,
                    d.name AS dest_name
                FROM trips t
                  LEFT JOIN stops o ON t.origin_stop_id = o.stop_id
                  LEFT JOIN stops d ON t.dest_stop_id = d.stop_id
                WHERE t.user_id = :user_id
                ORDER BY t.planned_start DESC
                FETCH FIRST 20 ROWS ONLY
                """
            ),
            {"user_id": user_id},
        ).all()

    trips = []
    for r in rows:
        trips.append(
            {
                "trip_id": r.trip_id,
                "planned_start": r.planned_start,
                "planned_end": r.planned_end,
                "origin_name": r.origin_name,
                "dest_name": r.dest_name,
                "line_id": r.line_id,
            }
        )

    if not trips:
        return templates.TemplateResponse(
            "history.html",
            {
                "request": request,
                "user": current_user,
                "trips": [],
            },
        )

    trip_ids = [t["trip_id"] for t in trips]
    extra_data_by_trip = {}
    mongo_trips = mongo_db["trips"].find(
        {"_id": {"$in": trip_ids}},
        {"_id": 1, "lines_used": 1, "total_distance": 1, "distance_unit": 1},
    )
    for doc in mongo_trips:
        extra_data_by_trip[doc["_id"]] = doc

    
    profile = ensure_mongo_profile(mongo_db, user_id)
    target_pref = profile.get("prefs", {}).get("units", "metric") 

    # Merge data and apply unit conversions (if needed)
    for t in trips:
        mongo_doc = extra_data_by_trip.get(t["trip_id"], {})
        
        # Lines Logic
        lines = mongo_doc.get("lines_used", [])
        if not lines and t["line_id"]:
            lines = [t["line_id"]]
        t["lines"] = lines

        # distance conversion logic
        dist = mongo_doc.get("total_distance", 0.0)
        stored_unit = mongo_doc.get("distance_unit", "km") 

        
        
        # Stored as km, User wants Imperial 
        if stored_unit == "km" and target_pref == "imperial":
            dist = dist * 0.621371
            stored_unit = "mi"
            
        # Stored as mi, User wants Metric 
        elif stored_unit == "mi" and target_pref == "metric":
            dist = dist * 1.60934
            stored_unit = "km"
            

        t["total_distance"] = round(dist, 2)
        t["distance_unit"] = stored_unit

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "user": current_user,
            "trips": trips,
        },
    )

@app.get("/plan", response_class=HTMLResponse)
def plan_page(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "plan.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, current_user=Depends(get_current_user)):
    
    mongo_profile = ensure_mongo_profile(mongo_db, current_user["user_id"])

    favorites = mongo_profile.get("favorites", {})
    fav_line_ids = favorites.get("lines", [])
    fav_stop_ids = favorites.get("stops", [])

    fav_line_ids = fav_line_ids or []
    fav_stop_ids = fav_stop_ids or []

    fav_line_ids_set = set(fav_line_ids)
    fav_stop_ids_set = set(fav_stop_ids)

    # Load Oracle data for all lines + all stops
    with get_engine().connect() as conn:
        lines_rows = conn.execute(
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
                ORDER BY line_mode, code
                """
            )
        ).mappings().all()

        stops_rows = conn.execute(
            text(
                """
                SELECT
                    stop_id,
                    code,
                    name
                FROM stops
                ORDER BY name
                """
            )
        ).mappings().all()

    # Mark favorites for UI
    all_lines = []
    for r in lines_rows:
        all_lines.append(
            {
                "line_id": r["line_id"],
                "code": r["code"],
                "name": r["name"],
                "mode": r["line_mode"],
                "is_favorite": r["line_id"] in fav_line_ids_set,
            }
        )

    all_stops = []
    for r in stops_rows:
        all_stops.append(
            {
                "stop_id": r["stop_id"],
                "code": r["code"],
                "name": r["name"],
                "is_favorite": r["stop_id"] in fav_stop_ids_set,
            }
        )

    prefs = mongo_profile.get("prefs", {})
    notify_disruptions = prefs.get("notifyDisruptions", True)
    units = prefs.get("units", "metric")

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
            "lines": all_lines,
            "stops": all_stops,
            "prefs": {
                "notifyDisruptions": notify_disruptions,
                "units": units,
            },
        },
    )


@app.get("/live", response_class=HTMLResponse)
def live_page(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "live.html",
        {
            "request": request,
            "user": current_user,
        },
    )


# ########################################################################################################################
# Existing SQL and NoSQL tests, to see if connections work (in Mongo section also check if collections are present)
# ########################################################################################################################

@app.get("/db-test")
def db_test():
    try:
        with get_engine().begin() as conn:
            result = conn.execute(text("SELECT 'OK' AS status, SYSDATE AS now FROM dual"))
            row = result.fetchone()
        return {
            "ok": True,
            "status": row.status,
            "now": str(row.now),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/redis-test")
def redis_test():
    try:
        ping = redis_client.ping()
        redis_client.set("test-key", "hello-redis")
        value = redis_client.get("test-key")
        return {"ok": True, "ping": ping, "test_value": value}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/mongo-test")
def mongo_test():
    try:
        lines_col = mongo_db["lines"]
        stops_col = mongo_db["stops"]
        vehicles_col = mongo_db["vehicles"]
        profiles_col = mongo_db["user_profiles"]
        trips_col = mongo_db["trips"]
        schedules_col = mongo_db["line_schedules"]

        # Basic counts
        lines_count = lines_col.count_documents({})
        stops_count = stops_col.count_documents({})
        vehicles_count = vehicles_col.count_documents({})
        profiles_count = profiles_col.count_documents({})
        trips_count = trips_col.count_documents({})
        schedules_count = schedules_col.count_documents({})

        # Samples 
        sample_line = lines_col.find_one({}, {"_id": 1, "code": 1, "name": 1, "mode": 1})
        sample_stop = stops_col.find_one({}, {"_id": 1, "code": 1, "name": 1})
        sample_vehicle = vehicles_col.find_one(
            {},
            {"_id": 1, "plate": 1, "model": 1, "capacity": 1, "line": 1, "lastKnown": 1},
        )

        # checks for vehicles
        vehicles_missing_lastKnown = vehicles_col.count_documents({"lastKnown": {"$exists": False}})
        vehicles_missing_model = vehicles_col.count_documents({"model": {"$exists": False}})
        vehicles_missing_capacity = vehicles_col.count_documents({"capacity": {"$exists": False}})
        vehicles_missing_line = vehicles_col.count_documents({"line": {"$exists": False}})

        # Check whether vehicle.line references a known line _id
        line_ids = lines_col.distinct("_id") if lines_count else []
        unknown_line_refs = (
            vehicles_col.count_documents({"line": {"$nin": line_ids}})
            if line_ids
            else vehicles_count
        )

        # how many vehicles have a lastKnown timestamp at all
        vehicles_with_lastKnown = vehicles_col.count_documents({"lastKnown.ts": {"$exists": True}})

        return {
            "ok": True,
            "counts": {
                "lines": lines_count,
                "stops": stops_count,
                "vehicles": vehicles_count,
                "user_profiles": profiles_count,
                "trips": trips_count,
                "line_schedules": schedules_count,
            },
            "samples": {
                "line": sample_line,
                "stop": sample_stop,
                "vehicle": sample_vehicle,
            },
            "vehicle_checks": {
                "missing_lastKnown": vehicles_missing_lastKnown,
                "missing_model": vehicles_missing_model,
                "missing_capacity": vehicles_missing_capacity,
                "missing_line": vehicles_missing_line,
                "unknown_line_refs": unknown_line_refs,
                "with_lastKnown_ts": vehicles_with_lastKnown,
            },
            "notes": [
                "If /api/live-vehicles filters by lastKnown.ts, missing_lastKnown can explain empty results.",
                "If /api/live-vehicles filters by line_id, unknown_line_refs can explain empty results.",
                "If you seeded vehicles without lastKnown, consider adding a default lastKnown for testing.",
            ],
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}
    

@app.get("/neo4j-test")
def neo4j_test():
    """
    Simple Neo4j healthcheck:
    - RUN `RETURN 1 AS ok`
    - Count nodes and relationships
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            # Basic ping
            ping_record = session.run("RETURN 1 AS ok").single()
            ping_ok = ping_record["ok"]

            # Counts (just for sanity)
            node_count_record = session.run(
                "MATCH (n) RETURN count(n) AS c"
            ).single()
            rel_count_record = session.run(
                "MATCH ()-[r]->() RETURN count(r) AS c"
            ).single()

            node_count = node_count_record["c"]
            rel_count = rel_count_record["c"]

        return {
            "ok": True,
            "ping": ping_ok,
            "nodes": node_count,
            "relationships": rel_count,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }