from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from typing import List
from dotenv import load_dotenv
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Get the project root directory (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """
    Application settings class that loads and validates environment variables.
    All settings are loaded from environment variables with fallback values.
    """
    # Environment
    ENV: str = os.getenv("ENV", "development")
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5000"))
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "TruthLens API"
    VERSION: str = "1.0.0"
    
    # CORS Settings
    # In development, only allow localhost:5173. In production, only allow the Netlify domain.
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173" if os.getenv("ENV", "development") == "development" else "https://truthlensai.netlify.app/"
    ]
    
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Serper API Settings
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    SERPER_API_URL: str = "https://google.serper.dev/search"
    
    # ElevenLabs Settings
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io/v1"
    ELEVENLABS_MODEL_ID: str = os.getenv("ELEVENLABS_MODEL_ID", "turbo_v2")
    ELEVENLABS_AGENT_ID: str = os.getenv("AGENT_ID", "")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Test Settings
    TEST_API_BASE_URL: str = os.getenv("TEST_API_BASE_URL", "http://localhost:8000")
    
    def validate_settings(self) -> None:
        """
        Validate critical settings and log warnings for missing or invalid values.
        """
        if not self.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set. API functionality will be limited.")
        
        if not self.SERPER_API_KEY:
            logger.warning("SERPER_API_KEY is not set. Search functionality will be limited.")
        
        if not self.ELEVENLABS_API_KEY:
            logger.warning("ELEVENLABS_API_KEY is not set. Voice translation will not work.")
        
        if not self.BACKEND_CORS_ORIGINS:
            logger.warning("No CORS origins configured. API may not be accessible from frontend.")
    
    class Config:
        case_sensitive = True
        env_file = str(PROJECT_ROOT / ".env")
        extra = "allow"  # Allow extra fields in the settings model

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings instance
    """
    settings = Settings()
    settings.validate_settings()
    return settings

settings = get_settings() 