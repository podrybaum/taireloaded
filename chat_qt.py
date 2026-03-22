from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLineEdit, QLabel, QFrame
from PySide6.QtCore import Qt, Slot
from bus import Bus

class ChatOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 0)
        
        # Message History Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setWidgetResizable(True)
        
        # User Input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.layout.addWidget(self.scroll)
        self.layout.addWidget(self.input_field)
        
        self.setStyleSheet("""
            QWidget { background-color: #1a1a1e; color: #e0e0e0; }
            QLineEdit { 
                background-color: #222228;
                border: 1px solid #333; 
                border-radius: 20px; 
                padding: 10px 15px; 
                margin-top: 5px;
                color: white;
            }
            QScrollArea { background: transparent; }
        """)

    def send_message(self):
        text = self.input_field.text().strip()
        if text:
            from message_classes import UserMessage
            Bus.emit("new_message", UserMessage(text))
            self.input_field.clear()

    @Slot(object)
    def post_message(self, message):
        # In Pass 1, we just show the text. In Pass 2, we'll use bubble widgets.
        msg_label = QLabel(f"<b>{getattr(message, 'sender', 'User')}:</b> {getattr(message, 'text', str(message))}")
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("padding: 5px; background: #2a2a30; border-radius: 8px;")
        self.scroll_layout.addWidget(msg_label)
        
        # Auto-scroll to bottom
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
