# app/db/neo4j.py

from neo4j import GraphDatabase
from app.config import settings

_driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
)


def get_driver():
    """Return the shared Neo4j driver."""
    return _driver
