import sys
import json
import asyncio
import threading
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QObject
import websockets

class WebSocketClient(QObject):
    message_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)

    def __init__(self, uri):
        super().__init__()
        self.uri = uri
        self.is_connected = False
        self.send_queue = None

    async def _send_worker(self, websocket):
        while True:
            cmd = await self.send_queue.get()
            await websocket.send(json.dumps(cmd))
            self.send_queue.task_done()

    async def connect(self):
        while True:
            try:
                self.status_changed.emit("Connecting...")
                async with websockets.connect(self.uri) as websocket:
                    self.is_connected = True
                    self.status_changed.emit("Connected")
                    
                    # Start a background task to handle sending messages
                    send_task = asyncio.create_task(self._send_worker(websocket))
                    
                    try:
                        while True:
                            message = await websocket.recv()
                            data = json.loads(message)
                            self.message_received.emit(data)
                    finally:
                        send_task.cancel()
            except Exception as e:
                self.is_connected = False
                self.status_changed.emit(f"Disconnected (Retry in 3s)")
                print(f"WebSocket Client error: {e}")
                await asyncio.sleep(3)

    def start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.send_queue = asyncio.Queue()
        self.loop.run_until_complete(self.connect())

    def send_command(self, action):
        if hasattr(self, 'loop') and self.loop.is_running() and self.send_queue:
            asyncio.run_coroutine_threadsafe(
                self.send_queue.put({"type": "command", "action": action}),
                self.loop
            )

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ws_client = None # Initialize as None
        self.init_ui()
        self.start_websocket()

    def init_ui(self):
        # Removed Qt.WindowType.Tool as it can cause the window to disappear on some macOS versions
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 450, 350)
        
        layout = QVBoxLayout()
        
        # Header with status and close button
        header_layout = QHBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #888; font-size: 10px; font-family: Arial, sans-serif;")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        # Control Buttons
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setFixedSize(30, 24)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px;")
        self.pause_btn.clicked.connect(self.toggle_pause)
        header_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹️")
        self.stop_btn.setFixedSize(30, 24)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px;")
        self.stop_btn.clicked.connect(self.stop_session)
        header_layout.addWidget(self.stop_btn)
        
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 50, 50, 150);
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 50, 50, 255);
            }
        """)
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)
        
        layout.addLayout(header_layout)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 180);
                color: #00FF00;
                font-family: 'Courier New', monospace;
                font-size: 15px;
                border: 2px solid #00FF00;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        
        self.text_edit.setText("System: Waiting for backend connection...")

    def start_websocket(self):
        self.ws_thread = threading.Thread(target=self._run_ws, daemon=True)
        self.ws_thread.start()

    def _run_ws(self):
        self.ws_client = WebSocketClient("ws://127.0.0.1:8000/ws")
        self.ws_client.message_received.connect(self.update_text)
        self.ws_client.status_changed.connect(self.update_status)
        self.ws_client.start()

    def update_status(self, status):
        self.status_label.setText(status)
        if status == "Connected":
            self.text_edit.append("\n[System]: Connected to backend. Listening for audio...")
        elif "Disconnected" in status:
            self.pause_btn.setText("⏸️")

    def toggle_pause(self):
        if not self.ws_client: return
        if self.pause_btn.text() == "⏸️":
            self.pause_btn.setText("▶️")
            self.status_label.setText("Paused")
            self.ws_client.send_command("pause")
        else:
            self.pause_btn.setText("⏸️")
            self.status_label.setText("Listening")
            self.ws_client.send_command("play")

    def stop_session(self):
        if not self.ws_client: return
        self.status_label.setText("Stopped")
        self.text_edit.append("\n[System]: Session Stopped.")
        self.ws_client.send_command("stop")
        self.pause_btn.setText("⏸️")

    def update_text(self, data):
        transcript = data.get("transcript", "")
        suggestion = data.get("suggestion", "")
        
        if transcript:
            self.text_edit.append(f"\n[Transcript]: {transcript}")
        if suggestion:
            self.text_edit.append(f"<b>AI Copilot:</b> {suggestion}")
        
        # Auto-scroll
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    sys.exit(app.exec())
