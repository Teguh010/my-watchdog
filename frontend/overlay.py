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

    async def connect(self):
        while True:
            try:
                self.status_changed.emit("Connecting...")
                async with websockets.connect(self.uri) as websocket:
                    self.is_connected = True
                    self.status_changed.emit("Connected")
                    print(f"Connected to {self.uri}")
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        self.message_received.emit(data)
            except Exception as e:
                self.is_connected = False
                self.status_changed.emit(f"Disconnected (Retry in 3s)")
                print(f"WebSocket Client error: {e}")
                await asyncio.sleep(3)

    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect())

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
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
