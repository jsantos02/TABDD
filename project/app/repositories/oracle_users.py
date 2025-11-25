# app/repositories/oracle_users.py

import uuid
from passlib.context import CryptContext
from sqlalchemy import text

from app.db.oracle import get_engine  # your lazy Oracle engine

# Switched from bcrypt to pbkdf2_sha256
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
