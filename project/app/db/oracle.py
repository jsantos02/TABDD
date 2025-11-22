# app/db/oracle.py

from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings

# Lazy singleton engine
_engine: Optional[Engine] = None


def get_engine() -> Engine:

    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.ORACLE_DSN,
            pool_pre_ping=True,
            future=True,
            
        )
    return _engine
