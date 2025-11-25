# app/db/neo4j_db.py

from neo4j import GraphDatabase
from app.config import settings

neo4j_driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
)
