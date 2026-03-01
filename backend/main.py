import asyncio
from fastapi import FastAPI, WebSocket
from backend.audio_capture import AudioCapturer
from backend.stt_module import STTModule
from backend.gemini_service import GeminiService
import uvicorn
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global instances (simplified for boilerplate)
stt = STTModule()
gemini = GeminiService()
capturer = AudioCapturer(device_name="BlackHole 2ch")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Frontend connected via WebSocket.")
    
    # Start capturer only if not already running
    if not capturer.is_running:
        logger.info("Starting audio capturer...")
        capturer.start()
    
    audio_buffer = bytearray()
    buffer_limit = 16000 * 2 * 10 # 10 seconds of audio (16k rate * 2 bytes/sample * 10s)
    
    try:
        while True:
            audio_chunk = capturer.get_audio_chunk()
            if audio_chunk:
                audio_buffer.extend(audio_chunk)
                
                if len(audio_buffer) >= buffer_limit:
                    logger.info(f"Processing {len(audio_buffer)} bytes of audio...")
                    try:
                        transcript = stt.transcribe(bytes(audio_buffer))
                        logger.info(f"Raw Transcript: '{transcript}'") # Always log raw result
                    except Exception as e:
                        logger.error(f"STT Error: {e}")
                        transcript = ""
                        
                    audio_buffer = bytearray() # Clear buffer
                    
                    # Filter out common hallucinations during silence
                    hallucinations = ["You", "Thank you", "Gebeld.", "you"]
                    if transcript.strip() in hallucinations:
                        logger.info(f"Filtered out hallucination: '{transcript}'")
                        transcript = ""

                    # Be slightly less restrictive for testing
                    if transcript and len(transcript.strip()) > 5:
                        logger.info(f"Sending to Gemini: {transcript}")
                        try:
                            response = gemini.get_response(transcript)
                            logger.info(f"Gemini Response: {response}")
                            
                            await websocket.send_json({
                                "transcript": transcript,
                                "suggestion": response
                            })
                        except Exception as e:
                            logger.error(f"Gemini API Error: {e}")
                    else:
                        logger.info("Transcript too short or empty, skipping Gemini.")
            
            await asyncio.sleep(0.01)
            
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")
    finally:
        logger.info("WebSocket session ended.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
