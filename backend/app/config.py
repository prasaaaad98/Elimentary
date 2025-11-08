from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    DATABASE_URL: str = "sqlite:///./balancesheet.db"

    class Config:
        env_file = ".env"


settings = Settings()
