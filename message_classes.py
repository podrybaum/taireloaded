from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from theme import THEME


def get_chat_css():
    """Generates the base CSS for the WebView chat, matching the Indigo Dark theme."""
    return f"""
        body {{
            background-color: transparent;
            color: {THEME["ui_text"]};
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 10px;
            padding-bottom: 20px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            gap: 12px;
        }}
        .message-row:first-child {{
            margin-top: auto;
        }}
        /* Hide default scrollbar or style it transparently */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: transparent;
        }}
        ::-webkit-scrollbar-thumb {{
            background: rgba(98, 77, 125, 0.4);
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(98, 77, 125, 0.6);
        }}
        .message-row {{
            display: flex;
            width: 100%;
            margin-bottom: 15px;
        }}
        .domme {{ 
            flex-direction: row; 
            align-items: flex-start;
        }}
        .user {{ 
            flex-direction: row-reverse; 
            align-items: flex-end;
        }}
        .system, .emote {{ justify-content: center; text-align: center; }}
        
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 20px;
            margin: 0 10px;
            background-color: {THEME["ui_primary"]};
        }}
        
        .msg-content {{
            display: flex;
            flex-direction: column;
            max-width: 70%;
        }}
        .domme .msg-content {{ align-items: flex-start; }}
        .user .msg-content {{ align-items: flex-end; }}
        
        .sender-info {{
            font-size: 11px;
            opacity: 0.7;
            margin-bottom: 2px;
        }}
        
        .bubble {{
            padding: 10px 14px;
            border-radius: 16px;
            font-size: 14px;
            line-height: 1.4;
            word-wrap: break-word;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .domme .bubble {{
            background-color: {THEME["highlighted_shadow"]};
            border-top-left-radius: 0;
        }}
        .user .bubble {{
            background-color: {THEME["highlighted_disabled"]};
            border-bottom-right-radius: 0;
        }}
        
        .system .bubble, .emote .bubble {{
            background: transparent;
            box-shadow: none;
            font-style: italic;
            opacity: 0.8;
            padding: 2px;
        }}
        .emote .bubble {{ color: #b683f6; }}
        
        .timestamp {{
            font-size: 10px;
            opacity: 0.5;
            margin-top: 4px;
        }}
    """


def get_message_html(sender, text, msg_type="domme"):
    """Generates the HTML fragment for a single message."""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    avatar_url = "ui_resources/user_avatar.png"  # Standard local path

    # Map types to legacy-friendly class names
    css_class = msg_type.lower()

    avatar_html = f'<img src="{avatar_url}" class="avatar">' if css_class in ["domme", "user"] else ""
    sender_html = f'<div class="sender-info">{sender} said:</div>' if css_class in ["domme", "user"] else ""
    time_html = f'<div class="timestamp">{timestamp}</div>' if css_class in ["domme", "user"] else ""

    return f"""
    <div class="message-row {css_class}">
        {avatar_html}
        <div class="msg-content">
            {sender_html}
            <div class="bubble">
                {text}
            </div>
            {time_html}
        </div>
    </div>
    """


class ChatMessage(QWidget):
    def __init__(self, sender="", text="", parent=None):
        super().__init__(parent)
        self.sender = str(sender)
        self.text = text
        self.timestamp = datetime.now().strftime("%H:%M")  # Shorter timestamp for cleaner UI

        # Main Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)

        # Avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(32, 32)
        self.avatar_label.setScaledContents(True)

        # Message Container (Sender Name + Bubble + Timestamp)
        self.msg_container = QVBoxLayout()
        self.msg_container.setSpacing(2)

        # Sender Label
        self.name_label = QLabel(f"{self.sender} said:")
        self.name_label.setStyleSheet("color: #b0b0b0; font-size: 10px;")

        # Bubble Frame
        self.bubble = QFrame()
        self.bubble_layout = QVBoxLayout(self.bubble)
        self.bubble_layout.setContentsMargins(12, 10, 12, 10)

        self.text_label = QLabel(self.text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: white; font-size: 13px; background: transparent;")
        self.bubble_layout.addWidget(self.text_label)

        # Timestamp
        self.time_label = QLabel(self.timestamp)
        self.time_label.setStyleSheet("color: #808080; font-size: 9px;")

        self.msg_container.addWidget(self.name_label)
        self.msg_container.addWidget(self.bubble)
        self.msg_container.addWidget(self.time_label)

    def finish_init(self, msg_type):
        avatar_path = "ui_resources/user_avatar.png"  # Default

        if msg_type == "domme":
            # Domme: Avatar Left, Bubble Blue/Shadow
            self.bubble.setObjectName("DommeBubble")
            self.bubble.setStyleSheet(f"""
                #DommeBubble {{
                    background-color: {THEME["highlighted_shadow"]};
                    border-radius: 16px;
                    border-top-left-radius: 0px;
                }}
            """)
            self.avatar_label.setPixmap(QPixmap(avatar_path))
            self.main_layout.addWidget(self.avatar_label, alignment=Qt.AlignTop)
            self.main_layout.addLayout(self.msg_container)
            self.main_layout.addStretch()
            self.name_label.setAlignment(Qt.AlignLeft)
            self.time_label.setAlignment(Qt.AlignLeft)

        elif msg_type == "user":
            # User: Avatar Right, Bubble Greyish/Indigo
            self.bubble.setObjectName("UserBubble")
            self.bubble.setStyleSheet(f"""
                #UserBubble {{
                    background-color: {THEME["highlighted_disabled"]};
                    border-radius: 16px;
                    border-bottom-right-radius: 0px;
                }}
            """)
            self.avatar_label.setPixmap(QPixmap(avatar_path))
            self.main_layout.addStretch()
            self.main_layout.addLayout(self.msg_container)
            self.main_layout.addWidget(self.avatar_label, alignment=Qt.AlignBottom)
            self.name_label.setAlignment(Qt.AlignRight)
            self.time_label.setAlignment(Qt.AlignRight)


class DommeMessage(ChatMessage):
    def __init__(self, sender, text="", parent=None):
        super().__init__(sender, text, parent)
        self.finish_init("domme")


class UserMessage(ChatMessage):
    def __init__(self, text="", parent=None):
        self.sender = "You"
        super().__init__(self.sender, text, parent)
        self.finish_init("user")


class SystemMessage(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.text = f"System Message: {text}"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)

        self.label = QLabel(f"<i>{self.text}</i>")
        self.label.setStyleSheet("color: #808080; font-size: 13px;")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)


class EmoteMessage(QWidget):
    def __init__(self, sender, text, parent=None):
        super().__init__(parent)
        self.text = text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)

        sender_name = sender.name if hasattr(sender, "name") else str(sender)
        self.label = QLabel(f"<i>*{sender_name} {text}*</i>")
        self.label.setStyleSheet("color: #b683f6; font-size: 13px;")  # Lavender for emotes
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
