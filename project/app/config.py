import os

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # matches ISEP docker config
    ORACLE_USER: str = "system"
    ORACLE_PASSWORD: str = "oracle"
    ORACLE_HOST: str = "vsgate-s1.dei.isep.ipp.pt"
    ORACLE_PORT: int = 10969
    ORACLE_SERVICE: str = "XE"

    @property
    def ORACLE_DSN(self) -> str:
        return (
            f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}"
            f"@{self.ORACLE_HOST}:{self.ORACLE_PORT}"
            f"/?service_name={self.ORACLE_SERVICE}"
        )
    
    # matches docker: redis-local on port 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL_SECONDS: int = 3600 # 1 hour session TTL

    # matches docker: mongo-local on port 27017
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "urban_transport"

    # matches docker: neo4j-local
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    class Config:
        env_file = ".env"

settings = Settings()