# app/config.py

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar



import os



class Settings(BaseSettings):
    # 🔧 Autoriser des variables en plus dans le .env
    env_file: ClassVar[str] = ".env" if os.path.exists(os.path.join(os.path.dirname(__file__), "..", ".env")) else ".env.example"
    model_config = SettingsConfigDict(
        env_file=env_file,
        env_file_encoding="utf-8",
        extra="ignore"   
    )

    openai_api_key: str
    openai_model: str 

    telegram_api_id: int
    telegram_api_hash: str
    telegram_session: str

    sources_telegram: str 

    max_messages_per_channel: int = 50
    batch_size: int = 20

    # Langue cible pour la traduction (ex: fr, es, de)
    target_language: str = "fr"


@lru_cache
def get_settings() -> Settings:
    return Settings()
