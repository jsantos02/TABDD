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
from typing import Optional, List, Dict
from app.db.oracle import get_engine
from app.db.redis import redis_client
from app.config import settings
from app.repositories import oracle_users, oracle_sessions
from datetime import datetime, timedelta, timezone
from app.db.mongo import mongo_db, mongo_client
from app.db.neo4j import get_driver
from app.services.travel_history import create_trip_polyglot



app = FastAPI(title="Porto Transport App")
templates = Jinja2Templates(directory="app/templates")


# ---------------------------
# Pydantic models for JSON APIs
# ---------------------------

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


# ---------------------------
# Session helpers (Redis)
# ---------------------------

SESSION_PREFIX = "session:"


def create_session(user_id: str, request: Request) -> str:
    """
    Create a session:
    - Insert row into Oracle user_sessions (for history / auditing)
    - Store token->user_id in Redis for fast runtime auth
    """
    token = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=settings.SESSION_TTL_SECONDS)

    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None

    # 1) Persist in Oracle
    oracle_sessions.create_user_session(
        session_id=token,
        user_id=user_id,
        issued_at=now,
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
    )

    # 2) Store active session in Redis (fast lookup)
    redis_client.setex(
        SESSION_PREFIX + token,
        settings.SESSION_TTL_SECONDS,
        user_id,
    )

    return token




def get_user_id_from_token(token: str | None) -> str | None:
    if not token:
        return None

    # 1) Fast path: Redis
    user_id = redis_client.get(SESSION_PREFIX + token)
    if user_id:
        return user_id

    # 2) Fallback: Oracle user_sessions (in case Redis lost the key)
    session = oracle_sessions.get_active_session(token)
    if not session:
        return None  # no such session or already expired in Oracle

    user_id = session["user_id"]

    # 3) Re-hydrate Redis with remaining TTL (optional but nice)
    expires_at = session["expires_at"]
    # expires_at is a datetime from Oracle; use UTC-ish delta
    now = datetime.now(datetime.timezone.utc)
    ttl_seconds = int((expires_at - now).total_seconds())

    if ttl_seconds > 0:
        redis_client.setex(SESSION_PREFIX + token, ttl_seconds, user_id)

    return user_id


async def get_current_user(request: Request):
    # 1) Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # 2) session_token cookie
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


# ---------------------------
# HTML pages
# ---------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Home page:
    - If user has a valid session cookie -> render index.html
    - Otherwise -> redirect to /login
    """
    token = request.cookies.get("session_token")
    user = None

    if token:
        user_id = get_user_id_from_token(token)
        if user_id:
            user = oracle_users.get_user_by_id(user_id)

    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


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


# ---------- NEW: HTML Register page ----------

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": None},
    )


@app.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    """
    Handles the HTML register form (register.html).
    Creates user in Oracle and logs them in (creates Redis session).
    """
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

    # auto-login: create session and redirect to home
    token = create_session(user_id, request)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=settings.SESSION_TTL_SECONDS,
    )
    return response

# ---------------------------
# JSON auth API (for Postman, etc.)
# ---------------------------

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


@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")

    if token:
        # 1) remove from Redis
        redis_client.delete(SESSION_PREFIX + token)

        # 2) remove from Oracle (hard delete)
        deleted = oracle_sessions.delete_user_session(token)
        # if you want to debug, you can temporarily print:
        # print(f"Deleted {deleted} session rows for {token}")

        # (If you prefer soft delete, use expire_user_session(token) instead.)

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response



@app.get("/me")
def me(current_user=Depends(get_current_user)):
    """
    Protected endpoint to confirm the session is working.
    """
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "is_active": current_user["is_active"],
    }


@app.get("/api/lines/{line_id}")
def line_detail(line_id: str, current_user=Depends(get_current_user)):
    """
    Return Mongo-only line document.

    Example doc:
    {
      "_id": "LINE_M_A",
      "code": "A",
      "name": "...",
      "mode": "metro",
      "itinerary": [...],
      "alerts": [...]
    }
    """
    doc = mongo_db.lines.find_one({"_id": line_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Line not found in MongoDB")

    # Optional: convert _id to plain string (it already is, but this is safe)
    doc["_id"] = str(doc["_id"])

    return doc


@app.get("/api/oracle/lines/{line_id}") # oracle only
def oracle_line_detail(line_id: str, current_user=Depends(get_current_user)):
    """
    Oracle-only view of a line:
    - line row from Oracle 'lines' table
    - ordered itinerary from 'stop_times' + 'stops'
    """
    with get_engine().begin() as conn:
        # 1) Fetch the line from Oracle
        line_row = conn.execute(
            text(
                """
                SELECT
                    line_id,
                    code,
                    name,
                    line_mode,
                    active
                FROM lines
                WHERE line_id = :line_id
                """
            ),
            {"line_id": line_id},
        ).mappings().first()

        if not line_row:
            raise HTTPException(status_code=404, detail="Line not found in Oracle")

        # 2) Fetch ordered stops for this line
        stops_rows = conn.execute(
            text(
                """
                SELECT
                    s.stop_id,
                    s.code       AS stop_code,
                    s.name       AS stop_name,
                    s.lat,
                    s.lon,
                    st.scheduled_seconds_from_start AS seconds_from_start
                FROM stop_times st
                JOIN stops s ON s.stop_id = st.stop_id
                WHERE st.line_id = :line_id
                ORDER BY st.scheduled_seconds_from_start
                """
            ),
            {"line_id": line_id},
        ).mappings().all()

    return {
        "line": dict(line_row),
        "stops": [dict(r) for r in stops_rows],
    }

@app.post("/api/trips")
def create_trip(
    trip: TripCreate,
    current_user=Depends(get_current_user),
):
    """
    Create a trip for the logged-in user.

    - Writes main record into Oracle `trips`
    - Mirrors summary into MongoDB:
        - `trips` collection
        - `user_profiles.recentTrips` (rolling list)
    """
    user_id = current_user["user_id"]
    now = datetime.now(timezone.utc)
    trip_id = str(uuid.uuid4())

    # --------------------------
    # 1) Oracle: main history
    # --------------------------
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO trips (
                    trip_id,
                    user_id,
                    line_id,
                    origin_stop_id,
                    dest_stop_id,
                    planned_start,
                    planned_end,
                    created_at
                ) VALUES (
                    :trip_id,
                    :user_id,
                    :line_id,
                    :origin_stop_id,
                    :dest_stop_id,
                    :planned_start,
                    :planned_end,
                    :created_at
                )
                """
            ),
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

    # --------------------------
    # 2) MongoDB: mirror trips
    # --------------------------
    trips_col = mongo_db["trips"]
    trips_col.insert_one(
        {
            "_id": trip_id,
            "user_id": user_id,
            "line_id": trip.line_id,
            "origin_stop": trip.origin_stop_id,
            "dest_stop": trip.dest_stop_id,
            "planned_start": trip.planned_start,
            "planned_end": trip.planned_end,
            "created_at": now,
        }
    )

    # --------------------------
    # 3) MongoDB: user_profiles.recentTrips
    #    (rolling list, e.g. last 10)
    # --------------------------
    profiles = mongo_db["user_profiles"]
    profiles.update_one(
        {"_id": user_id},
        {
            # if user_profile does not exist, create base structure
            "$setOnInsert": {
                "favorites": {"lines": [], "stops": []},
                "prefs": {"notifyDisruptions": False, "units": "metric"},
            },
            # push latest trip, keep only last 10
            "$push": {
                "recentTrips": {
                    "$each": [
                        {
                            "trip_id": trip_id,
                            "at": now,
                            "origin": trip.origin_stop_id,
                            "dest": trip.dest_stop_id,
                        }
                    ],
                    "$slice": -10,
                }
            },
        },
        upsert=True,
    )

    return {
        "ok": True,
        "trip_id": trip_id,
        "user_id": user_id,
    }


@app.get("/api/route")
def get_route(
    origin_stop_id: str,
    dest_stop_id: str,
    current_user=Depends(get_current_user),
):
    driver = get_driver()

    with driver.session() as session:
        result = session.run(
            """
            MATCH (origin:Stop { stop_id: $origin_id }),
                  (dest:Stop   { stop_id: $dest_id })
            MATCH p = shortestPath(
                (origin)-[:NEXT|TRANSFER*..50]->(dest)
            )
            RETURN p AS path
            """,
            origin_id=origin_stop_id,
            dest_id=dest_stop_id,
        )
        record = result.single()

        if record is None:
            raise HTTPException(status_code=404, detail="No route found between those stops")

        path = record["path"]
        nodes = list(path.nodes)
        rels = list(path.relationships)

    segments = []
    total_travel_s = 0
    lines_used = []

    for idx, rel in enumerate(rels):
        from_node = nodes[idx]
        to_node = nodes[idx + 1]

        # Relationship type in Neo4j 5:
        rel_type = rel.type  # "NEXT" or "TRANSFER"

        # Relationship properties: treat missing as 0
        avg_travel_s = rel.get("avg_travel_s", 0) if hasattr(rel, "get") else rel.get("avg_travel_s") if "avg_travel_s" in rel else 0  # defensive
        walk_s = rel.get("walk_s", 0) if hasattr(rel, "get") else rel.get("walk_s") if "walk_s" in rel else 0  # defensive
        line_id = rel.get("line_id") if hasattr(rel, "get") else rel.get("line_id") if "line_id" in rel else None

        cost = (avg_travel_s or 0) + (walk_s or 0)
        total_travel_s += cost

        if line_id and line_id not in lines_used:
            lines_used.append(line_id)

        if walk_s and rel_type == "TRANSFER":
            # For transfers, we may not have a line_id
            line_id = "WALK TO TRANSFER"
        segments.append(
            {
                "rel_type": rel_type,
                "from_stop": {
                    "stop_id": from_node.get("stop_id"),
                    "code": from_node.get("code"),
                    "name": from_node.get("name"),
                },
                "to_stop": {
                    "stop_id": to_node.get("stop_id"),
                    "code": to_node.get("code"),
                    "name": to_node.get("name"),
                },
                "line_id": line_id,
                "avg_travel_s": avg_travel_s,
                "walk_s": walk_s,
                "cost_s": cost,
            }
        )

    return {
        "origin_stop_id": origin_stop_id,
        "dest_stop_id": dest_stop_id,
        "total_hops": len(rels),
        "total_travel_s": total_travel_s,
        "lines_used": lines_used,
        "segments": segments,
    }

# -----------------------------
# Lines and History html endpoint
# -----------------------------

@app.get("/lines", response_class=HTMLResponse)
async def lines_page(request: Request):
    """
    Shows all lines from Oracle in a table (lines.html).
    Requires the user to be logged in (session cookie).
    """
    token = request.cookies.get("session_token")
    user = None

    if token:
        user_id = get_user_id_from_token(token)
        if user_id:
            user = oracle_users.get_user_by_id(user_id)

    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # ---- SIMPLIFIED QUERY HERE ----
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
def history_page(
    request: Request,
    user: dict = Depends(get_current_user),
):
    if not user:
        # Optionally redirect to /login, but for now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = user["user_id"]

    # 1) Oracle: authoritative trip rows
    with get_engine().begin() as conn:
        result = conn.execute(
            text("""
                SELECT
                    t.trip_id,
                    t.planned_start,
                    t.planned_end,
                    l.code      AS line_code,
                    l.name      AS line_name,
                    s_orig.name AS origin_name,
                    s_dest.name AS dest_name
                FROM trips t
                LEFT JOIN lines l
                  ON t.line_id = l.line_id
                LEFT JOIN stops s_orig
                  ON t.origin_stop_id = s_orig.stop_id
                LEFT JOIN stops s_dest
                  ON t.dest_stop_id = s_dest.stop_id
                WHERE t.user_id = :user_id
                ORDER BY t.planned_start DESC
            """),
            {"user_id": user_id},
        )

        trips = [
            {
                "trip_id": row.trip_id,
                "line_code": row.line_code,
                "line_name": row.line_name,
                "origin_name": row.origin_name,
                "dest_name": row.dest_name,
                "planned_start": row.planned_start,
                "planned_end": row.planned_end,
            }
            for row in result
        ]

    # 2) Mongo: optional user profile + recentTrips
    profiles_coll = mongo_db["user_profiles"]
    profile = profiles_coll.find_one({"_id": user_id}) or {}
    recent_trips_mongo = profile.get("recentTrips", [])

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "trips": trips,
            "recent_trips_mongo": recent_trips_mongo,  # you can use this if you want
            "user": user,
        },
    )

# ---------------------------
# Existing DB / Redis tests
# ---------------------------

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
        lines_count = mongo_db.lines.count_documents({})
        stops_count = mongo_db.stops.count_documents({})
        sample = mongo_db.lines.find_one({}, {"_id": 1, "code": 1, "name": 1})

        return {
            "ok": True,
            "lines_count": lines_count,
            "stops_count": stops_count,
            "sample_line": sample,
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