from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

# Paksa baca .env sebelum apapun
load_dotenv(override=True)


class Settings(BaseSettings):
    # App
    app_name: str = "Credit Risk Scoring Platform"
    app_env: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str
    async_database_url: str

    # Redis / Celery
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str

    # LLM — Ollama (local)
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "qwen2.5:7b"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"

    # MLflow
    mlflow_tracking_uri: str = "./data/mlflow"
    mlflow_experiment_name: str = "credit-risk-scoring"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Grafana
    grafana_url: str = ""
    grafana_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()