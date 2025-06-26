from fastapi import APIRouter, HTTPException
from app.models.schemas import TranslationRequest, TranslationResponse
from app.prompts.translation_prompts import get_translation_prompt
from app.services.openai_service import OpenAIService
from elevenlabs.client import ElevenLabs
import os, uuid, json, logging
from datetime import datetime
from typing import Dict, Optional
from app.services.storage_service import StorageService
from app.services.cache_manager import CacheManager

router = APIRouter(
    prefix="/translator",
    tags=["translator"],
    responses={404: {"description": "Not found"}},
)

openai_service = OpenAIService()
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
logger = logging.getLogger(__name__)
storage_service = StorageService()
cache_manager = CacheManager(storage_service)

# Cache for available voices
_available_voices: Optional[Dict[str, str]] = None

def get_voice_for_language(lang: str) -> str:
    """
    Get the most appropriate voice ID for the given language.
    First tries to find a voice that matches the language exactly,
    then falls back to a default voice if no match is found.
    """
    global _available_voices
    
    # If we haven't fetched voices yet, do it now
    if _available_voices is None:
        try:
            voices_response = elevenlabs_client.voices.get_all()
            voices = voices_response[0] if isinstance(voices_response, tuple) else voices_response
            _available_voices = {}
            for voice in voices:
                # Try to get language info from different possible attributes
                lang_code = None
                if hasattr(voice, 'labels') and voice.labels and 'language' in voice.labels:
                    lang_code = voice.labels['language'].lower()
                elif hasattr(voice, 'language'):
                    lang_code = getattr(voice, 'language').lower()
                if lang_code:
                    _available_voices[lang_code] = voice.voice_id
            logger.info(f"Loaded {len(_available_voices)} voices from ElevenLabs")
        except Exception as e:
            logger.error(f"Error fetching voices from ElevenLabs: {e}")
            # Fallback to default voices if API call fails
            _available_voices = {
                "es": "TxGEqnHWrfWFTfGW9XjX",  # Spanish
                "en": "21m00Tcm4TlvDq8ikWAM",  # English
                "fr": "MF3mGyEYCl7XYWbV9V6O",  # French
                "it": "yoZ06aMxZJJ28mfd3POQ",  # Italian
                "pt": "ODq5zmih8GrVes37Dizd",  # Portuguese
                "de": "ErXwobaYiN019PkySvjV"   # German
            }
    
    # Try to find a voice for the exact language
    voice_id = _available_voices.get(lang.lower())
    if voice_id:
        return voice_id
    
    # If no exact match, try to find a voice that starts with the language code
    for voice_lang, vid in _available_voices.items():
        if voice_lang.startswith(lang.lower()):
            return vid
    
    # If still no match, use English as fallback
    logger.warning(f"No voice found for language {lang}, using English as fallback")
    return _available_voices.get("en", "21m00Tcm4TlvDq8ikWAM")

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Translate text from source language to target language using the specified translation mode.
    """
    try:
        # Get translation from GPT using the modularized prompt
        response = await openai_service.client.chat.completions.create(
            model=openai_service.model,
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": get_translation_prompt(
                    style=request.translation_mode,
                    target_lang=request.target_language,
                    text=request.text
                )}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        translated_text = response.choices[0].message.content.strip()
        logger.info(f"Text translated successfully from: {request.source_language} to: {request.target_language}")
        # Save input and result to database
        storage_service.save_analysis(
            tipo_analisis="traduccion",
            input_original=request.text,
            resultado={
                "translated_text": translated_text,
                "source_language": request.source_language,
                "target_language": request.target_language,
                "translation_mode": request.translation_mode
            }
        )
        return TranslationResponse(
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            translation_mode=request.translation_mode
        )
    except ValueError as ve:
        logger.error(f"Invalid translation style: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail="Error during translation. Please try again.")

@router.post("/translate-voice")
async def translate_and_generate_voice(request: TranslationRequest):
    logger.info(f"Received request: {request}")
    try:
        # Clean up old files periodically
        storage_service.cleanup_old_files(max_age_hours=24)
        
        # 1. Generate prompt and log
        prompt = get_translation_prompt(
            style=request.translation_mode,
            target_lang=request.target_language,
            text=request.text
        )
        logger.info(f"Generated prompt: {prompt}")

        # 2. Translation with OpenAI
        response = await openai_service.client.chat.completions.create(
            model=openai_service.model,
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        translated_text = response.choices[0].message.content.strip()
        logger.info(f"Translated text: {translated_text}")

        # 3. Voice selection
        voice_id = get_voice_for_language(request.target_language)
        logger.info(f"Selected voice_id: {voice_id} for language: {request.target_language}")

        # 4. Audio generation
        audio_gen = elevenlabs_client.text_to_speech.convert(
            text=translated_text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        # 5. Save audio file using storage service
        uid = str(uuid.uuid4())
        audio_filename = f"voice_{uid}.mp3"
        
        # Collect audio data
        audio_data = b""
        for chunk in audio_gen:
            audio_data += chunk
        
        # Save audio file
        audio_path = storage_service.save_audio_file(audio_data, audio_filename)
        logger.info(f"Audio file saved: {audio_path}")

        # 6. Save metadata
        metadata = {
            "original_text": request.text,
            "translated_text": translated_text,
            "source_language": request.source_language,
            "target_language": request.target_language,
            "translation_mode": request.translation_mode,
            "voice_id": voice_id,
            "timestamp": datetime.now().isoformat()
        }
        metadata_filename = f"translation_{uid}.json"
        storage_service.save_metadata(metadata, metadata_filename)
        logger.info(f"Metadata saved for id: {uid}")

        # 7. Save to database
        storage_service.save_analysis(
            tipo_analisis="traduccion_voz",
            input_original=request.text,
            resultado={
                "translated_text": translated_text,
                "source_language": request.source_language,
                "target_language": request.target_language,
                "translation_mode": request.translation_mode,
                "voice_id": voice_id,
                "audio_filename": audio_filename
            }
        )

        return {
            "translated_text": translated_text,
            "audio_url": f"/static/voice_{uid}.mp3",
            "id": uid
        }

    except Exception as e:
        logger.error(f"Error in translate-and-generate-voice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Translation or voice generation failed")

@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics including file count, total size, and file information.
    """
    try:
        stats = cache_manager.get_cache_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving cache statistics")

@router.post("/cache/cleanup")
async def cleanup_cache(max_age_hours: int = 24):
    """
    Manually trigger cache cleanup.
    
    Args:
        max_age_hours: Maximum age of files to keep (default: 24 hours)
    """
    try:
        await cache_manager.cleanup_cache(max_age_hours)
        return {
            "status": "success",
            "message": f"Cache cleanup completed. Files older than {max_age_hours} hours were removed."
        }
    except Exception as e:
        logger.error(f"Error during manual cache cleanup: {e}")
        raise HTTPException(status_code=500, detail="Error during cache cleanup")

@router.post("/cache/cleanup/start")
async def start_cache_cleanup_scheduler(cleanup_interval_hours: int = 1):
    """
    Start the automatic cache cleanup scheduler.
    
    Args:
        cleanup_interval_hours: How often to run cleanup (default: 1 hour)
    """
    try:
        # Start the scheduler in the background
        import asyncio
        asyncio.create_task(cache_manager.start_cleanup_scheduler(cleanup_interval_hours))
        
        return {
            "status": "success",
            "message": f"Cache cleanup scheduler started with {cleanup_interval_hours} hour interval"
        }
    except Exception as e:
        logger.error(f"Error starting cache cleanup scheduler: {e}")
        raise HTTPException(status_code=500, detail="Error starting cache cleanup scheduler")

@router.post("/cache/cleanup/stop")
async def stop_cache_cleanup_scheduler():
    """
    Stop the automatic cache cleanup scheduler.
    """
    try:
        await cache_manager.stop_cleanup_scheduler()
        return {
            "status": "success",
            "message": "Cache cleanup scheduler stopped"
        }
    except Exception as e:
        logger.error(f"Error stopping cache cleanup scheduler: {e}")
        raise HTTPException(status_code=500, detail="Error stopping cache cleanup scheduler") 