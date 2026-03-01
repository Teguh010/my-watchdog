import asyncio
from fastapi import FastAPI, WebSocket
from backend.audio_capture import AudioCapturer
from backend.stt_module import STTModule
from backend.gemini_service import GeminiService
import uvicorn
import json
import logging
import numpy as np

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
    
    # New session: reset AI history
    gemini.reset_history()
    
    # Start capturer only if not already running
    if not capturer.is_running:
        logger.info("Starting audio capturer...")
        capturer.start()
    
    audio_buffer = bytearray()
    buffer_limit = 16000 * 2 * 15 # Max 15 seconds if no silence detected
    SILENCE_THRESHOLD = 50 
    SILENCE_DURATION_TRIGGER = 1.5 # Seconds of silence to trigger processing
    
    silence_counter = 0
    chunk_count = 0
    
    state = {"paused": False, "stopped": False}

    async def receiver():
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "command":
                    action = data.get("action")
                    if action == "pause":
                        state["paused"] = True
                        logger.info("Session PAUSED")
                    elif action == "play":
                        state["paused"] = False
                        logger.info("Session RESUMED")
                    elif action == "stop":
                        state["stopped"] = True
                        logger.info("Session STOPPED")
        except Exception as e:
            logger.error(f"Receiver error: {e}")

    # Start receiver task
    receiver_task = asyncio.create_task(receiver())
    
    try:
        while not state["stopped"]:
            audio_chunk = capturer.get_audio_chunk()
            if audio_chunk and not state["paused"]:
                audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
                energy = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                
                chunk_count += 1
                if chunk_count % 100 == 0:
                    logger.info(f"Audio Energy: {energy:.1f}")

                if energy > SILENCE_THRESHOLD:
                    audio_buffer.extend(audio_chunk)
                    silence_counter = 0 # Reset silence counter when sound is heard
                else:
                    if len(audio_buffer) > 0:
                        silence_counter += 0.1 # chunks are approx 0.1s in our capturer loop (1024/16000)
                
                # Trigger: Hit byte limit OR consistent silence after some speech
                should_process = len(audio_buffer) >= buffer_limit or (silence_counter >= SILENCE_DURATION_TRIGGER and len(audio_buffer) > 16000)

                if should_process:
                    logger.info(f"Processing {len(audio_buffer)} bytes (Silence trigger: {silence_counter >= SILENCE_DURATION_TRIGGER})")
                    try:
                        transcript = stt.transcribe(bytes(audio_buffer))
                        logger.info(f"Raw Transcript: '{transcript}'")
                    except Exception as e:
                        logger.error(f"STT Error: {e}")
                        transcript = ""
                        
                    audio_buffer = bytearray() 
                    silence_counter = 0
                    
                    hallucinations = [
                        "You", "Thank you", "Gebeld.", "you", "Subtitles by", 
                        "Amara.org", "Watch for more", "Please subscribe",
                        "Thanks for watching", "We're back."
                    ]
                    if transcript.strip() in hallucinations:
                        logger.info(f"Filtered out hallucination: '{transcript}'")
                        transcript = ""

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
        receiver_task.cancel()
        logger.info("WebSocket session ended.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
