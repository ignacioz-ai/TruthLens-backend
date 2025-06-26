from typing import Dict, Optional
import json
import os
import tempfile
import shutil
from datetime import datetime
import logging
from supabase import create_client, Client
from ..core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        # Use absolute paths and create a proper temp directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.storage_dir = os.path.join(self.base_dir, "app", "data", "temp")
        
        # Create temp directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Fallback to system temp directory if the above fails
        if not os.access(self.storage_dir, os.W_OK):
            self.storage_dir = tempfile.gettempdir()
            logger.warning(f"Using system temp directory: {self.storage_dir}")
        
        self.current_article_id = None
        
        # Initialize Supabase client
        try:
            self.supabase: Client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
        except Exception as e:
            logger.error(f"Error connecting to Supabase: {str(e)}")
            self.supabase = None

    def get_temp_path(self, filename: str) -> str:
        """Get absolute path for a temporary file."""
        return os.path.join(self.storage_dir, filename)

    def save_audio_file(self, audio_data: bytes, filename: str) -> str:
        """Save audio file to temp directory and return the full path."""
        file_path = self.get_temp_path(filename)
        try:
            with open(file_path, "wb") as f:
                f.write(audio_data)
            logger.info(f"Audio file saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving audio file {filename}: {e}")
            raise

    def save_metadata(self, metadata: Dict, filename: str) -> str:
        """Save metadata JSON file to temp directory."""
        file_path = self.get_temp_path(filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"Metadata saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving metadata {filename}: {e}")
            raise

    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old files from temp directory."""
        current_time = datetime.now()
        cleaned_count = 0
        
        try:
            for filename in os.listdir(self.storage_dir):
                file_path = os.path.join(self.storage_dir, filename)
                
                # Skip if not a file
                if not os.path.isfile(file_path):
                    continue
                
                # Check file age
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                age_hours = (current_time - file_time).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(f"Old file deleted: {filename}")
                    except Exception as e:
                        logger.error(f"Error deleting file {filename}: {str(e)}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old files")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def save_article(self, text: str, analysis: Optional[Dict] = None) -> str:
        """Saves the article and its analysis, returns the article ID."""
        article_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_article_id = article_id
        
        data = {
            "text": text,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
        
        file_path = os.path.join(self.storage_dir, f"{article_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Article saved with ID: {article_id}")
        return article_id

    def get_article(self, article_id: Optional[str] = None) -> Optional[Dict]:
        """Gets the article and its analysis by ID."""
        if article_id is None:
            article_id = self.current_article_id
        
        if article_id is None:
            return None
            
        file_path = os.path.join(self.storage_dir, f"{article_id}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Article not found: {article_id}")
            return None

    def get_current_article(self) -> Optional[Dict]:
        """Gets the current article."""
        return self.get_article(self.current_article_id)

    def clear_old_articles(self, max_age_hours: int = 24):
        """Cleans articles older than max_age_hours."""
        current_time = datetime.now()
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(self.storage_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            age_hours = (current_time - file_time).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                try:
                    os.remove(file_path)
                    logger.info(f"Old article deleted: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting article {filename}: {str(e)}")

    def save_analysis(
        self,
        tipo_analisis: str,
        input_original: str,
        resultado: dict,
        usuario: str = None,
        es_publico: bool = False
    ) -> None:
        """
        Saves the analysis to Supabase database and locally as backup.
        """
        data = {
            "fecha": datetime.now().isoformat(),
            "tipo_analisis": tipo_analisis,
            "input_original": input_original,
            "resultado": resultado,
            "usuario": usuario,
            "es_publico": es_publico
        }
        # Save locally as backup
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.storage_dir, f"{backup_id}_analysis.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Save to Supabase if available
        if self.supabase:
            try:
                self.supabase.table("analisis").insert(data).execute()
                logger.info(f"Analysis saved in Supabase: {tipo_analisis}")
            except Exception as e:
                logger.error(f"Error saving analysis in Supabase: {str(e)}") 