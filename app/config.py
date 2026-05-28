from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/rfmotor"
    SECRET_KEY: str   = "dev-secret-change-in-production"
    ALGORITHM: str    = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 dias
    BCB_API_BASE: str = "https://api.bcb.gov.br/dados/serie"
    ANBIMA_API_BASE: str = "https://www.anbima.com.br/informacoes/est-termo"

    class Config:
        env_file = ".env"

settings = Settings()
