# app/repositories/oracle_users.py

import uuid
from passlib.context import CryptContext
from sqlalchemy import text
from app.db.oracle import get_engine  
# Cryptographic context for password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def get_user_by_email(email: str):
    sql = text("""
        SELECT user_id, email, password_hash, full_name, role, is_active
        FROM users
        WHERE email = :email
    """)
    with get_engine().begin() as conn:
        row = conn.execute(sql, {"email": email}).fetchone()
        return dict(row._mapping) if row else None

def get_user_by_id(user_id: str):
    sql = text("""
        SELECT user_id, email, password_hash, full_name, role, is_active
        FROM users
        WHERE user_id = :user_id
    """)
    with get_engine().begin() as conn:
        row = conn.execute(sql, {"user_id": user_id}).fetchone()
        return dict(row._mapping) if row else None

def create_user(email: str, password: str, full_name: str, role: str = "passenger"):
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    sql = text("""
        INSERT INTO users (
            user_id, email, password_hash, full_name, role, created_at, is_active
        )
        VALUES (
            :user_id, :email, :password_hash, :full_name, :role, SYSTIMESTAMP, 1
        )
    """)
    with get_engine().begin() as conn:
        conn.execute(
            sql,
            {
                "user_id": user_id,
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "role": role,
            },
        )
    return user_id

def get_all_users():
    sql = text("""
        SELECT user_id, email, full_name, role, is_active, created_at
        FROM users
        ORDER BY created_at DESC
    """)
    with get_engine().begin() as conn:
        rows = conn.execute(sql).mappings().all()
        return [dict(row) for row in rows]

def update_user_status(user_id: str, is_active: bool):
    sql = text("""
        UPDATE users
        SET is_active = :is_active
        WHERE user_id = :user_id
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, {"is_active": 1 if is_active else 0, "user_id": user_id})
