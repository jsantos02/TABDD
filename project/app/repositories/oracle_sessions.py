# app/repositories/oracle_sessions.py

from datetime import datetime
from typing import Optional
from sqlalchemy import text

from app.db.oracle import get_engine


def create_user_session(
    session_id: str,
    user_id: str,
    issued_at: datetime,
    expires_at: datetime,
    user_agent: Optional[str],
    ip: Optional[str],
) -> None:
    if user_agent and len(user_agent) > 4000:
        user_agent = user_agent[:4000]

    sql = text("""
        INSERT INTO user_sessions (
            session_id, user_id, issued_at, expires_at, user_agent, ip
        )
        VALUES (
            :session_id, :user_id, :issued_at, :expires_at, :user_agent, :ip
        )
    """)
    with get_engine().begin() as conn:
        conn.execute(
            sql,
            {
                "session_id": session_id,
                "user_id": user_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
                "user_agent": user_agent,
                "ip": ip,
            },
        )


def expire_user_session(session_id: str) -> int:
    """
    Mark session expired by setting expires_at = SYSTIMESTAMP.
    Returns number of affected rows.
    """
    sql = text("""
        UPDATE user_sessions
        SET expires_at = SYSTIMESTAMP
        WHERE session_id = :session_id
    """)
    with get_engine().begin() as conn:
        result = conn.execute(sql, {"session_id": session_id})
        return result.rowcount


def delete_user_session(session_id: str) -> int:
    """
    Physically delete a session row.
    """
    sql = text("""
        DELETE FROM user_sessions
        WHERE session_id = :session_id
    """)
    with get_engine().begin() as conn:
        result = conn.execute(sql, {"session_id": session_id})
        return result.rowcount


def get_active_session(session_id: str) -> Optional[dict]:
    """
    Return session row if it exists AND is not expired yet.
    """
    sql = text("""
        SELECT session_id, user_id, issued_at, expires_at
        FROM user_sessions
        WHERE session_id = :session_id
          AND expires_at > SYSTIMESTAMP
    """)
    with get_engine().begin() as conn:
        row = conn.execute(sql, {"session_id": session_id}).fetchone()
        return dict(row._mapping) if row else None
