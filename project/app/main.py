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

from app.db.oracle import get_engine
from app.db.redis import redis_client
from app.config import settings
from app.repositories import oracle_users


app = FastAPI(title="Urban Transport App")

# Jinja2 templates (make sure your HTML files are in app/templates/)
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


# ---------------------------
# Session helpers (Redis)
# ---------------------------

SESSION_PREFIX = "session:"


def create_session(user_id: str) -> str:
    token = str(uuid.uuid4())
    redis_client.setex(
        SESSION_PREFIX + token,
        settings.SESSION_TTL_SECONDS,
        user_id,
    )
    return token


def get_user_id_from_token(token: str | None) -> str | None:
    if not token:
        return None
    return redis_client.get(SESSION_PREFIX + token)


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

    token = create_session(user["user_id"])

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
    token = create_session(user_id)
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
def api_login(data: LoginRequest):
    user = oracle_users.get_user_by_email(data.email)
    if not user or not oracle_users.verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_session(user["user_id"])

    response = JSONResponse({"access_token": token, "token_type": "bearer"})
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=settings.SESSION_TTL_SECONDS,
    )
    return response


from fastapi.responses import RedirectResponse

# ... keep the rest of your imports / code ...


@app.get("/logout")
async def logout(request: Request):
    # remove session from Redis
    token = request.cookies.get("session_token")
    if token:
        redis_client.delete(SESSION_PREFIX + token)

    # remove cookie and redirect to login
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
