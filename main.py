from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.api.routes import analyze, chat, translator
import logging
import os
from fastapi import WebSocket
from app.websockets.voice_handler import handle_voice_websocket
from dotenv import load_dotenv
from pathlib import Path
from app.routes import image_analysis
from app.services.storage_service import StorageService
from app.services.cache_manager import CacheManager
import asyncio
from typing import Optional

# Configure logging for application-wide error tracking and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize rate limiter to prevent API abuse
limiter = Limiter(key_func=get_remote_address)

load_dotenv()
logger.debug("Environment variables loaded")

class VoiceAssistantManager:
    def __init__(self):
        self.elevenlabs_api_key = settings.ELEVENLABS_API_KEY
        self.elevenlabs_agent_id = settings.ELEVENLABS_AGENT_ID
        self.elevenlabs_base_url = settings.ELEVENLABS_BASE_URL
        self.model_id = settings.ELEVENLABS_MODEL_ID

# Global cache manager instance
cache_manager: Optional[CacheManager] = None

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application with all necessary middleware and routes.
    
    Returns:
        FastAPI: Configured FastAPI application instance with CORS, rate limiting, and error handling
    """
    # Disable docs in production environment for security
    docs_url = "/docs" if settings.ENV != "production" else None
    redoc_url = "/redoc" if settings.ENV != "production" else None
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="API for analyzing news articles and detecting bias",
        version=settings.VERSION,
        docs_url=docs_url,
        redoc_url=redoc_url
    )

    # Configure rate limiting middleware to protect API endpoints
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Configure CORS middleware to allow frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files directory for audio files using StorageService
    storage_service = StorageService()
    static_dir = storage_service.storage_dir
    logger.info(f"Mounting static files from: {static_dir}")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Initialize cache manager
    global cache_manager
    cache_manager = CacheManager(storage_service)

    @app.on_event("startup")
    async def startup_event():
        """Initialize cache manager on startup."""
        try:
            # Start automatic cache cleanup scheduler
            asyncio.create_task(cache_manager.start_cleanup_scheduler(cleanup_interval_hours=2))
            logger.info("Cache cleanup scheduler started")
        except Exception as e:
            logger.error(f"Error starting cache cleanup scheduler: {e}")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up cache manager on shutdown."""
        try:
            if cache_manager:
                await cache_manager.stop_cleanup_scheduler()
                logger.info("Cache cleanup scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping cache cleanup scheduler: {e}")

    @app.get("/")
    async def root():
        """
        Root endpoint that provides basic API information and available endpoints.
        """
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.VERSION,
            "docs": "/docs",
            "endpoints": {
                "analyze": f"{settings.API_V1_STR}/analyze",
                "chat": f"{settings.API_V1_STR}/chat"
                # "health": f"{settings.API_V1_STR}/health"  # Health check disabled to save tokens
            }
        }

    # Health check endpoint disabled to save tokens
    """
    @app.get(f"{settings.API_V1_STR}/health")
    async def health_check():
        Health check endpoint to verify the API is running and monitor its status.
        return {
            "status": "healthy",
            "version": settings.VERSION
        }
    """

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Global exception handler for unhandled exceptions to provide consistent error responses.
        
        Args:
            request: The request that caused the exception
            exc: The exception that was raised
        """
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # Include API routers for different functionality
    app.include_router(analyze.router, prefix=settings.API_V1_STR, tags=["analysis"])
    app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["chat"])
    app.include_router(translator.router, prefix=settings.API_V1_STR, tags=["translator"])
    app.include_router(image_analysis.router, prefix="/api", tags=["image-analysis"])

    # Voice WebSocket endpoint
    @app.websocket("/ws/voice")
    async def voice_websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for voice assistant"""
        await handle_voice_websocket(websocket)

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting TruthLens API server...")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )