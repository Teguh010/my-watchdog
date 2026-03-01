import pyaudio
import numpy as np
import threading
import queue

class AudioCapturer:
    def __init__(self, device_name="BlackHole 2ch", rate=16000, chunk_size=1024):
        self.rate = rate
        self.chunk_size = chunk_size
        self.device_name = device_name
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.device_index = self._find_device_index()

    def _find_device_index(self):
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            if self.device_name in dev['name']:
                print(f"Found input device: {dev['name']} at index {i}")
                return i
        print(f"Warning: {self.device_name} not found. Using default input device.")
        return None

    def start(self):
        if self.is_running and self.stream:
            return
        self.is_running = True
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._callback
        )
        self.stream.start_stream()

    def _callback(self, in_data, frame_count, time_info, status):
        if self.is_running:
            self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()

    def get_audio_chunk(self):
        try:
            return self.audio_queue.get(timeout=1.0)
        except queue.Empty:
            return None
