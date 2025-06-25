from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/voice/generate")
async def generate_voice(text: str):
    """
    Mock endpoint que simula la generación de voz.
    Devuelve un archivo de audio predefinido para testing.
    """
    try:
        # Ruta al archivo de audio mock
        audio_path = os.path.join("static", "sounds", "speech.mp3")
        
        if not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Mock audio file not found")
            
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=response.mp3"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice/agent-id")
async def get_agent_id():
    agent_id = os.getenv("AGENT_ID")
    if not agent_id:
        return {"error": "Agent ID not configured"}
    return {"agent_id": agent_id} 