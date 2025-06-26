import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from .storage_service import StorageService

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Manages automatic cache cleanup and maintenance.
    """
    
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def start_cleanup_scheduler(self, cleanup_interval_hours: int = 1):
        """
        Start the automatic cleanup scheduler.
        
        Args:
            cleanup_interval_hours: How often to run cleanup (default: 1 hour)
        """
        if self.is_running:
            logger.warning("Cleanup scheduler is already running")
            return
            
        self.is_running = True
        logger.info(f"Starting cache cleanup scheduler (interval: {cleanup_interval_hours} hours)")
        
        while self.is_running:
            try:
                # Run cleanup
                await self.cleanup_cache()
                
                # Wait for next cleanup cycle
                await asyncio.sleep(cleanup_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in cache cleanup scheduler: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def stop_cleanup_scheduler(self):
        """Stop the automatic cleanup scheduler."""
        self.is_running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache cleanup scheduler stopped")
    
    async def cleanup_cache(self, max_age_hours: int = 24):
        """
        Clean up old cache files.
        
        Args:
            max_age_hours: Maximum age of files to keep (default: 24 hours)
        """
        try:
            logger.info(f"Starting cache cleanup (max age: {max_age_hours} hours)")
            
            # Use the storage service cleanup method
            self.storage_service.cleanup_old_files(max_age_hours)
            
            logger.info("Cache cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def get_cache_stats(self) -> dict:
        """
        Get statistics about the current cache.
        
        Returns:
            dict: Cache statistics including file count and total size
        """
        try:
            import os
            from pathlib import Path
            
            cache_dir = Path(self.storage_service.storage_dir)
            if not cache_dir.exists():
                return {
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "oldest_file": None,
                    "newest_file": None
                }
            
            files = list(cache_dir.glob("*"))
            file_count = len(files)
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            # Get oldest and newest files
            file_times = []
            for f in files:
                if f.is_file():
                    file_times.append((f.stat().st_mtime, f.name))
            
            oldest_file = min(file_times)[1] if file_times else None
            newest_file = max(file_times)[1] if file_times else None
            
            return {
                "file_count": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_file": oldest_file,
                "newest_file": newest_file,
                "cache_directory": str(cache_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)} 