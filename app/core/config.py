from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import logging

# Configure logging
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 5000

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "TruthLens API"
    VERSION: str = "1.0.0"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "https://truthlensai.netlify.app"
    ]

    # OpenAI Settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"

    # Serper API Settings
    SERPER_API_KEY: str
    SERPER_API_URL: str = "https://google.serper.dev/search"

    # ElevenLabs Settings
    ELEVENLABS_API_KEY: str
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io/v1"
    ELEVENLABS_MODEL_ID: str = "turbo_v2"
    ELEVENLABS_AGENT_ID: str = ""

    # Supabase Settings
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Test Settings
    TEST_API_BASE_URL: str = "http://localhost:8000"

    class Config:
        case_sensitive = True
        env_file = ".env"  # Solo útil en desarrollo

@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    return settings

settings = get_settings() 