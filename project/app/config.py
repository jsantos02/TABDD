import os

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
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
    
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL_SECONDS: int = 3600 # 1 hour session TTL
    
    class Config:
        env_file = ".env"

settings = Settings()