from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://taskuser:taskpass@localhost:5432/taskdb"
    SECRET_KEY: str = "change-me-generate-a-long-random-value"
    POSTGRES_USER: str = "taskuser"
    POSTGRES_PASSWORD: str = "taskpass"
    POSTGRES_DB: str = "taskdb"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


settings = Settings()
