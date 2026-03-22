import os
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QDockWidget, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction

from bus import Bus
from media_player_qt import MediaPlayerWidget
from chat_qt import ChatOverlay
from img_tags_qt import ImageTagger
from settings_ui_qt import SettingsWindow
from metronome_qt import Metronome

GLOBAL_QSS = """
QMainWindow { background-color: #121212; }
QWidget#CentralWidget { background-color: #121212; }

/* Buttons */
QPushButton { 
    background-color: #1e1e1e; 
    color: #ffffff; 
    border: 1px solid #333333; 
    padding: 10px 15px; 
    border-radius: 6px; 
    font-size: 14px;
    font-weight: 500;
}
QPushButton:hover { 
    background-color: #2a2a2a; 
    border: 1px solid #3f51b5;
}
QPushButton:pressed {
    background-color: #3f51b5;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #121212;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3f51b5;
}

/* DockWidget */
QDockWidget { 
    border-right: 1px solid #222222; 
    color: #888888;
}
QDockWidget::title { 
    background: #121212; 
    padding: 10px; 
    border-bottom: 1px solid #222222;
}

/* Drawer Buttons - Specialized */
QWidget#DrawerContent QPushButton {
    text-align: left;
    padding-left: 20px;
    background: transparent;
    border: none;
    border-radius: 0px;
    height: 45px;
    color: #b0b0b0;
}
QWidget#DrawerContent QPushButton:hover {
    background-color: #1e1e1e;
    color: #3f51b5;
}

QLabel { color: #ffffff; }
"""

class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 0, 15, 0)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #1a1a1e; border-bottom: 1px solid #222;")
        
        self.title = QLabel("TeaseAI - REBORN")
        self.title.setStyleSheet("font-weight: bold; color: #3f51b5; font-size: 15px;")
        self.layout.addWidget(self.title)
        
        self.layout.addStretch()
        
        # Customize buttons
        btn_style = "QPushButton { background: transparent; border: none; font-size: 16px; color: #888; } QPushButton:hover { background: #333; color: white; }"
        
        self.min_btn = QPushButton("-")
        self.min_btn.setFixedSize(40, 40)
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(self.parent.showMinimized)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(40, 40)
        self.close_btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 16px; color: #888; } QPushButton:hover { background: #c62828; color: white; }")
        self.close_btn.clicked.connect(self.parent.close)
        
        self.layout.addWidget(self.min_btn)
        self.layout.addWidget(self.close_btn)
        
        self.start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.parent.move(self.parent.pos() + delta)
            self.start_pos = event.globalPosition().toPoint()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(1400, 850)
        
        # Initialize Core Components
        self.metronome = Metronome()
        self.tagger_window = None
        self.settings_window = None
        
        self.setStyleSheet(GLOBAL_QSS)

        # Central Widget
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Title Bar
        self.title_bar = TitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        
        # Content Layout
        self.content_container = QWidget()
        self.content_layout = QHBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.content_layout.setSpacing(15)
        self.main_layout.addWidget(self.content_container)
        
        # Navigation Drawer
        self.setup_drawer()
        
        # Media Player
        self.media_player = MediaPlayerWidget()
        self.content_layout.addWidget(self.media_player, stretch=7)
        
        # Chat Overlay
        self.chat = ChatOverlay()
        self.content_layout.addWidget(self.chat, stretch=3)
        
        # System Tray
        self.setup_tray()
        
        # Bus Events
        self.register_events()

    def setup_drawer(self):
        self.drawer = QDockWidget("DASHBOARD", self)
        self.drawer.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.drawer_content = QWidget()
        self.drawer_content.setObjectName("DrawerContent")
        self.drawer_layout = QVBoxLayout(self.drawer_content)
        self.drawer_layout.setContentsMargins(0, 5, 0, 0)
        self.drawer_layout.setSpacing(0)
        
        btn_personality = QPushButton("Select Personality")
        btn_personality.clicked.connect(lambda: Bus.emit("select_personality_clicked"))
        
        btn_start = QPushButton("Start Session")
        btn_start.clicked.connect(lambda: Bus.emit("start"))
        
        btn_tagger = QPushButton("Image Tagger")
        btn_tagger.clicked.connect(self._open_tagger)
        
        btn_settings = QPushButton("User Settings")
        btn_settings.clicked.connect(self._open_settings)
        
        self.drawer_layout.addWidget(btn_personality)
        self.drawer_layout.addWidget(btn_start)
        self.drawer_layout.addWidget(btn_tagger)
        self.drawer_layout.addWidget(btn_settings)
        self.drawer_layout.addStretch()
        
        self.drawer.setWidget(self.drawer_content)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.drawer)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Fallback icon if resource missing
        icon_path = os.path.join("ui_resources", "tray_icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        
        self.tray_menu = QMenu()
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.showNormal)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        
        self.tray_menu.addAction(restore_action)
        self.tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def register_events(self):
        Bus.register("new_message", self.on_new_message)
        # More registrations in Pass 2

    def on_new_message(self, message):
        # Forward to the chat widget
        self.chat.post_message(message)

    def _open_tagger(self):
        if not self.tagger_window:
            self.tagger_window = ImageTagger()
        self.tagger_window.show()

    def _open_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow()
        self.settings_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
