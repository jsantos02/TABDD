from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Request,
    Form,
    status,
)
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel, EmailStr
from sqlalchemy import text
import uuid
from typing import Optional, List 
from datetime import datetime, timedelta, timezone

from app.db.oracle import get_engine
from app.db.redis import redis_client
from app.config import settings
from app.repositories import oracle_users, oracle_sessions, oracle_lines, oracle_trips, oracle_ops, mongo_trips, mongo_profiles, mongo_feedback, mongo_lines
from app.services import routing_service, live_service, alert_service
from app.db.mongo import mongo_db
from app.db.neo4j import get_driver

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
    units: str = "metric"  # default to metric

class FeedbackCreate(BaseModel):
    usability_rating: int  
    satisfaction_rating: int  
    comments: Optional[str] = None

class AdminAlertCreate(BaseModel):
    line_id: str
    msg: str
    duration_minutes: int = 60

class DriverAssignmentCreate(BaseModel):
    driver_id: str
    vehicle_id: str
    line_id: str

class UserStatusUpdate(BaseModel):
    is_active: bool

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
    
    if not user["is_active"]:
        redis_client.delete(SESSION_PREFIX + token)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    
    return user


def get_current_admin(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Insufficient permissions"
        )
    return current_user


def set_secure_cookie(response: Response, key: str, value: str):
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        max_age=settings.SESSION_TTL_SECONDS,
        secure=True, 
        samesite="lax"
    )
# ##############################
# HTML pages for login and registration
# ##############################

# Home page redirects to login if user not logged in. Also alerts when favorite lines have disruptions will be done here to fullfill requirements
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    token = request.cookies.get("session_token")
    user = None
    alerts = []

    if token:
        user_id = get_user_id_from_token(token)
        if user_id:
            user = oracle_users.get_user_by_id(user_id)
            alerts = alert_service.get_active_user_alerts(user_id)

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
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    # Fetch User
    user = oracle_users.get_user_by_email(email)
    
    # Verify Credentials
    if not user or not oracle_users.verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=400,
        )

    # Check if Banned 
    if not user["is_active"]:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Account is deactivated"},
            status_code=403,
        )

    # Create Session
    token = create_session(user["user_id"], request)

    # Redirect with Secure Cookie
    response = RedirectResponse(url="/", status_code=302)
    set_secure_cookie(response, "session_token", token)
    
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
    return alert_service.get_active_user_alerts(current_user["user_id"])

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
    
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    token = create_session(user["user_id"], request)

    content = {"access_token": token, "token_type": "bearer"}
    response = JSONResponse(content)
    
    set_secure_cookie(response, "session_token", token)
    return response


@app.get("/api/lines")
def api_list_lines(_=Depends(get_current_user)):
    return oracle_lines.get_active_lines()

# find line in mongodb
@app.get("/api/lines/{line_id}")
def line_detail(line_id: str, _=Depends(get_current_user)):

    doc = mongo_lines.get_line_by_id(line_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Line not found in MongoDB")
    
    doc["_id"] = str(doc["_id"])

    return doc

# fallback oracle line detail
@app.get("/api/oracle/lines/{line_id}")
def oracle_line_detail(line_id: str, _=Depends(get_current_user)):
    data = oracle_lines.get_line_details(line_id)
    if not data:
        raise HTTPException(status_code=404, detail="Line not found")
    return data

@app.post("/api/trips")
def create_trip(trip: TripCreate, current_user=Depends(get_current_user)):
    user_id = current_user["user_id"]
    now = datetime.now(timezone.utc)
    trip_id = str(uuid.uuid4())

    # Prepare Lines Used Logic
    if trip.lines_used and len(trip.lines_used) > 0:
        lines_used = trip.lines_used
    elif trip.line_id:
        lines_used = [trip.line_id]
    else:
        lines_used = []

    # Oracle write
    oracle_trips.create_trip(trip_id, user_id, trip)
    
    # MongoDB Write 
    mongo_trip_doc = {
        "_id": trip_id,
        "user_id": user_id,
        "line_id": trip.line_id,
        "lines_used": lines_used,
        "origin_stop": trip.origin_stop_id,
        "dest_stop": trip.dest_stop_id,
        "planned_start": trip.planned_start,
        "planned_end": trip.planned_end,
        "created_at": now,
        "total_distance": trip.total_distance,
        "distance_unit": trip.distance_unit,
    }
    mongo_trips.create_trip(mongo_trip_doc)

    # Update User Profile 
    recent_trip_summary = {
        "trip_id": trip_id,
        "at": now,
        "origin": trip.origin_stop_id,
        "dest": trip.dest_stop_id,
        "lines": lines_used,
        "dist": trip.total_distance, 
        "unit": trip.distance_unit
    }
    mongo_trips.add_trip_to_user_history(user_id, recent_trip_summary)

    return {"ok": True, "trip_id": trip_id, "user_id": user_id}

@app.get("/api/route")
def get_route(origin_stop_id: str, dest_stop_id: str, current_user=Depends(get_current_user)):
    user_id = current_user["user_id"]
    profile = mongo_profiles.get_or_create_profile(user_id)
    units = profile.get("prefs", {}).get("units", "metric")
    
    result = routing_service.find_best_route(origin_stop_id, dest_stop_id, units)
    
    if not result:
        raise HTTPException(status_code=404, detail="No route found")
    return result

# Get stops
@app.get("/api/stops")
def list_stops(_=Depends(get_current_user)):
    return oracle_lines.get_all_stops()

# Let user set favorite lines
@app.post("/api/profile/favorites/lines")
def set_line_favorite(payload: LineFavoritePayload, current_user=Depends(get_current_user)):
    mongo_profiles.update_favorite_line(current_user["user_id"], payload.line_id, payload.favorite)
    return {"ok": True}

# favorite stops
@app.post("/api/profile/favorites/stops")
def set_stop_favorite(payload: StopFavoritePayload, current_user=Depends(get_current_user)):
    mongo_profiles.update_favorite_stop(current_user["user_id"], payload.stop_id, payload.favorite)
    return {"ok": True}

@app.post("/api/profile/prefs")
def set_prefs(payload: PrefsPayload,current_user=Depends(get_current_user),):
    mongo_profiles.update_preferences(current_user["user_id"], payload.notifyDisruptions, payload.units)
    return {"ok": True}


# ##############################
# Admin API Endpoints
# ##############################

@app.post("/api/admin/alerts")
def create_alert(payload: AdminAlertCreate, _=Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(minutes=payload.duration_minutes)
    
    new_alert = {
        "msg": payload.msg,
        "from": now,
        "to": end_time
    }
    
    modified_count = mongo_lines.add_alert(payload.line_id, new_alert)

    return {"ok": True, "modified": modified_count}

@app.post("/api/admin/users/{user_id}/status")
def toggle_user_status(user_id: str, payload: UserStatusUpdate, _=Depends(get_current_admin)):
    oracle_users.update_user_status(user_id, payload.is_active)
    return {"ok": True}

@app.post("/api/admin/assignments")
def create_assignment(payload: DriverAssignmentCreate, _=Depends(get_current_admin)):
    assignment_id = "ASG_" + str(uuid.uuid4())[:8]
    oracle_ops.create_assignment(assignment_id, payload.driver_id, payload.vehicle_id, payload.line_id)
    return {"ok": True, "assignment_id": assignment_id}

# ######################
# Live vehicles (Mongo)
# ######################
@app.get("/api/live/{line_id}")
def live_line(line_id: str, _=Depends(get_current_user)):
    result = live_service.calculate_positions(line_id)
    
    if "error" in result:
        # If the service returned an error dict, handle it
        raise HTTPException(status_code=404, detail=result["error"])
        
    return result

# ################################
# Other HTML endpoints
# ################################
 
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, current_user=Depends(get_current_admin)):
    users = oracle_users.get_all_users()
    lines = oracle_lines.get_active_lines()
    drivers = oracle_ops.get_all_drivers()
    vehicles = oracle_ops.get_active_vehicles()

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, "user": current_user,
        "users": users, "lines": lines, "drivers": drivers, "vehicles": vehicles
    })

@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request):
    return templates.TemplateResponse(
        "feedback.html",
        {"request": request},
    )

@app.post("/feedback", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    usability_rating: int = Form(...),
    satisfaction_rating: int = Form(...),
    comments: str = Form(""),
    current_user=Depends(get_current_user), 
):
    feedback_data = {
        "user_id": current_user["user_id"], 
        "usability_rating": usability_rating,
        "satisfaction_rating": satisfaction_rating,
        "comments": comments,
        "submitted_at": datetime.now(timezone.utc),
    }

    
    mongo_feedback.create_feedback(feedback_data)

    return templates.TemplateResponse(
        "feedback.html",
        {
            "request": request,
            "msg": "Thank you for your feedback!"
        },
    )

@app.get("/lines", response_class=HTMLResponse)
def lines_page(request: Request):

    token = request.cookies.get("session_token")
    user = None

    if token:
        user_id = get_user_id_from_token(token)
        if user_id:
            user = oracle_users.get_user_by_id(user_id)

    if not user:
        return RedirectResponse(url="/login", status_code=302)

    lines = oracle_lines.get_active_lines() 

    return templates.TemplateResponse("lines.html", {"request": request, "user": user, "lines": lines})

@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, current_user=Depends(get_current_user)):
    
    trips = oracle_trips.get_user_history(current_user["user_id"])

    # Handle empty history case
    if not trips:
        return templates.TemplateResponse(
            "history.html",
            {
                "request": request,
                "user": current_user,
                "trips": [],
            },
        )

    # Fetch enrichment data from MongoDB
    trip_ids = [t["trip_id"] for t in trips]
    
    extra_data_by_trip = mongo_trips.get_trip_details_by_ids(trip_ids)

    # Fetch User Preferences for Unit Conversion
    user_id = current_user["user_id"]
    profile = mongo_profiles.get_or_create_profile(user_id)
    target_pref = profile.get("prefs", {}).get("units", "metric") 

    # Merge Data & Apply Unit Logic
    for t in trips:
        mongo_doc = extra_data_by_trip.get(t["trip_id"], {})
        
        # Merge Lines Used
        lines = mongo_doc.get("lines_used", [])
        # Fallback to single line_id from Oracle if Mongo list is empty
        if not lines and t.get("line_id"):
            lines = [t["line_id"]]
        t["lines"] = lines

        # Distance & Unit Conversion Logic
        dist = mongo_doc.get("total_distance", 0.0)
        stored_unit = mongo_doc.get("distance_unit", "km") 

        # Convert if preference differs from stored unit
        if stored_unit == "km" and target_pref == "imperial":
            dist = dist * 0.621371
            stored_unit = "mi"
        elif stored_unit == "mi" and target_pref == "metric":
            dist = dist * 1.60934
            stored_unit = "km"
            
        t["total_distance"] = round(dist, 2)
        t["distance_unit"] = stored_unit

    # Render Template
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
    user_id = current_user["user_id"]

    # Fetch Profile 
    profile = mongo_profiles.get_or_create_profile(user_id)
    
    fav_lines_set = set(profile.get("favorites", {}).get("lines", []))
    fav_stops_set = set(profile.get("favorites", {}).get("stops", []))

    # Fetch All Data 
    all_lines = oracle_lines.get_active_lines()
    all_stops = oracle_lines.get_all_stops()

    # Mark Favorites for UI
    for l in all_lines:
        l["is_favorite"] = l["line_id"] in fav_lines_set
    
    for s in all_stops:
        s["is_favorite"] = s["stop_id"] in fav_stops_set

    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
            "lines": all_lines,
            "stops": all_stops,
            "prefs": profile.get("prefs", {}),
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