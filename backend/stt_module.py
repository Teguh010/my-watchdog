from faster_whisper import WhisperModel
import numpy as np
import io
import wave

class STTModule:
    def __init__(self, model_size="base"):
        # Run on CPU by default for broader compatibility, use "cuda" if GPU is available
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_data, rate=16000):
        # Convert raw PCM data to numpy array
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        segments, info = self.model.transcribe(audio_np, beam_size=5)
        
        text = ""
        for segment in segments:
            text += segment.text + " "
        
        return text.strip()
