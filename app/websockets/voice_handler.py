"""
Voice WebSocket handler for TruthLens
Integrates with ElevenLabs for real-time voice AI conversations
"""

import asyncio
import json
import logging
import os
import base64
import websockets
from typing import Optional, Dict, Any
import aiohttp
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import tempfile
import subprocess
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceAssistantManager:
    """Manages voice assistant connections and ElevenLabs integration"""
    
    def __init__(self):
        self.elevenlabs_api_key = settings.ELEVENLABS_API_KEY
        self.elevenlabs_agent_id = settings.ELEVENLABS_AGENT_ID
        self.elevenlabs_base_url = settings.ELEVENLABS_BASE_URL
        self.model_id = settings.ELEVENLABS_MODEL_ID  # Low-latency model
        
        # System prompt for the voice assistant
        self.system_prompt = """You are Alex, the voice assistant for TruthLens. 
        Speak in short, friendly, helpful sentences. 
        Respond in Spanish if the user speaks Spanish, otherwise respond in English. 
        Ask for clarification if something is unclear.
        Keep responses under 50 words for natural conversation flow.
        You help users understand news analysis, bias detection, and fact-checking."""
    
    async def handle_websocket_connection(self, websocket: WebSocket):
        """Handle a new WebSocket connection for voice chat"""
        await websocket.accept()
        logger.info("Voice WebSocket connection established")
        
        try:
            # 1. Get signed_url from ElevenLabs
            signed_url = await self._get_signed_url()
            if not signed_url:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Failed to get signed URL from ElevenLabs"
                }))
                await websocket.close()
                return
            logger.info("Obtained signed_url from ElevenLabs")

            # 2. Open WebSocket to ElevenLabs
            async with websockets.connect(signed_url) as eleven_ws:
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "message": "Voice assistant connected and ready"
                }))
                # 3. Launch tasks to forward messages in both directions
                user_to_eleven = asyncio.create_task(self._forward_user_to_eleven(websocket, eleven_ws))
                eleven_to_user = asyncio.create_task(self._forward_eleven_to_user(websocket, eleven_ws))
                done, pending = await asyncio.wait(
                    [user_to_eleven, eleven_to_user],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
        except WebSocketDisconnect:
            logger.info("Voice WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
    
    async def _get_signed_url(self):
        url = f"{self.elevenlabs_base_url}/convai/conversation/get-signed-url?agent_id={self.elevenlabs_agent_id}"
        headers = {"xi-api-key": self.elevenlabs_api_key}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("signed_url")
                    else:
                        logger.error(f"Failed to get signed_url: {resp.status} {await resp.text()}")
                        return None
        except Exception as e:
            logger.error(f"Exception getting signed_url: {e}")
            return None

    async def _forward_user_to_eleven(self, websocket: WebSocket, eleven_ws):
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"[PROXY] Message received from user: {data[:100]}...")
                message = json.loads(data)

                if message.get("type") == "user_audio_chunk":
                    if not all(k in message for k in ["audio", "audio_format"]):
                        logger.error("Incomplete audio message")
                        continue

                    # If audio comes in webm format, convert to PCM 16kHz 16-bit
                    if message["audio_format"] == "webm":
                        logger.info("Converting webm audio to PCM 16kHz 16-bit...")
                        pcm_b64 = self._convert_webm_base64_to_pcm_base64(message["audio"])
                        if not pcm_b64:
                            logger.error("Error converting webm to PCM")
                            continue
                        await eleven_ws.send(json.dumps({
                            "type": "user_audio_chunk",
                            "audio": pcm_b64,
                            "audio_format": "pcm_16000"
                        }))
                        logger.info("[PROXY] PCM audio chunk sent to ElevenLabs")
                    elif message["audio_format"] == "pcm_16000":
                        await eleven_ws.send(json.dumps({
                            "type": "user_audio_chunk",
                            "audio": message["audio"],
                            "audio_format": "pcm_16000"
                        }))
                        logger.info("[PROXY] PCM audio chunk sent to ElevenLabs (already in correct format)")
                    else:
                        logger.error(f"[PROXY] Unsupported audio format: {message['audio_format']}")
                        continue
                else:
                    await eleven_ws.send(data)
                    logger.info(f"[PROXY] Other type of message sent to ElevenLabs: {message.get('type')}")
            except Exception as e:
                logger.error(f"Error forwarding user->eleven: {e}")
                break

    def _convert_webm_base64_to_pcm_base64(self, webm_b64: str) -> str:
        try:
            webm_bytes = base64.b64decode(webm_b64)
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_file:
                webm_file.write(webm_bytes)
                webm_path = webm_file.name
            pcm_path = webm_path.replace('.webm', '.pcm')
            # ffmpeg: convert to PCM 16kHz 16-bit mono
            cmd = [
                'ffmpeg', '-y', '-i', webm_path,
                '-ac', '1', '-ar', '16000', '-f', 's16le', pcm_path
            ]
            subprocess.run(cmd, check=True)
            with open(pcm_path, 'rb') as pcm_file:
                pcm_bytes = pcm_file.read()
            # Clean temporary files
            os.remove(webm_path)
            os.remove(pcm_path)
            return base64.b64encode(pcm_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Error in ffmpeg conversion: {e}")
            return None

    async def _forward_eleven_to_user(self, websocket: WebSocket, eleven_ws):
        while True:
            try:
                data = await eleven_ws.recv()
                logger.info(f"[PROXY] Message received from ElevenLabs: {data[:100]}...")  # Only log first 100 characters
                
                # Parse the JSON message
                message = json.loads(data)
                message_type = message.get("type")
                
                # Handle different message types
                if message_type == "ping":
                    # Ignore pings, they're just to keep the connection alive
                    continue
                elif message_type == "audio":
                    # Verify we have the audio
                    audio_data = message.get("audio")
                    if not audio_data:
                        logger.error("Audio message without audio data")
                        continue
                        
                    # Send audio to client
                    response = {
                        "type": "audio_response",
                        "audio": audio_data,
                        "audio_format": message.get("audio_format", "mp3_44100_128")
                    }
                    logger.info(f"[PROXY] Sending audio response to user (size: {len(audio_data)})")
                    await websocket.send_text(json.dumps(response))
                elif message_type == "error":
                    error_msg = message.get("message", "Error from ElevenLabs")
                    logger.error(f"[PROXY] ElevenLabs error: {error_msg}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": error_msg
                    }))
                elif message_type == "conversation_initiation_metadata":
                    logger.info("[PROXY] Initialization metadata received")
                    await websocket.send_text(data)
                else:
                    # Log and re-send other types of messages
                    logger.info(f"[PROXY] Unhandled message type: {message_type}")
                    await websocket.send_text(data)
                
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from ElevenLabs: {e}")
                continue
            except Exception as e:
                logger.error(f"Error forwarding eleven->user: {e}")
                break
    
    async def _process_audio_input(self, websocket: WebSocket, message: Dict[str, Any]):
        """Process audio input from the client"""
        try:
            audio_data = message.get("audio")
            audio_format = message.get("format", "webm")
            
            if not audio_data:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "No audio data received"
                }))
                return
            
            # Send status update
            await websocket.send_text(json.dumps({
                "type": "status",
                "message": "Processing your voice..."
            }))
            
            # Process with ElevenLabs
            response_audio = await self._process_with_elevenlabs(audio_data, audio_format)
            
            if response_audio:
                # Send audio response back to client
                await websocket.send_text(json.dumps({
                    "type": "audio_response",
                    "audio": response_audio
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Failed to generate voice response"
                }))
                
        except Exception as e:
            logger.error(f"Error processing audio input: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Error processing your voice input"
            }))
    
    async def _process_with_elevenlabs(self, audio_data: str, audio_format: str) -> Optional[str]:
        """Process audio with ElevenLabs and return response audio"""
        try:
            if not self.elevenlabs_api_key or not self.elevenlabs_agent_id:
                logger.error("ElevenLabs credentials not configured")
                return None
            
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)
            
            # Use ElevenLabs Conversational AI endpoint
            url = f"{self.elevenlabs_base_url}/convai/conversation"
            
            headers = {
                "xi-api-key": self.elevenlabs_api_key,
                "Content-Type": "application/json"
            }
            
            # Prepare the request payload
            payload = {
                "agent_id": self.elevenlabs_agent_id,
                "audio": audio_data,
                "audio_format": audio_format,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.3,
                    "use_speaker_boost": True
                },
                "generation_config": {
                    "chunk_length_schedule": [120, 160, 250, 290]
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Extract audio from response
                        if "audio" in response_data:
                            return response_data["audio"]
                        else:
                            logger.error("No audio in ElevenLabs response")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"ElevenLabs API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error calling ElevenLabs API: {e}")
            return None
    
    async def _fallback_text_to_speech(self, text: str) -> Optional[str]:
        """Fallback text-to-speech using ElevenLabs TTS endpoint"""
        try:
            if not self.elevenlabs_api_key:
                return None
            
            # Use a default voice if agent_id is not available
            voice_id = self.elevenlabs_agent_id or "21m00Tcm4TlvDq8ikWAM"  # Default voice
            
            url = f"{self.elevenlabs_base_url}/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.3,
                    "use_speaker_boost": True
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        audio_bytes = await response.read()
                        return base64.b64encode(audio_bytes).decode('utf-8')
                    else:
                        error_text = await response.text()
                        logger.error(f"ElevenLabs TTS error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error in fallback TTS: {e}")
            return None

# Global instance
voice_manager = VoiceAssistantManager()

async def handle_voice_websocket(websocket: WebSocket):
    """FastAPI WebSocket endpoint handler"""
    await voice_manager.handle_websocket_connection(websocket) 