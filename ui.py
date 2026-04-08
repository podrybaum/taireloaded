import os
from settings import APPLICATION_ROOT
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSystemTrayIcon,
    QMenu,
    QStackedWidget,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PySide6.QtGui import QIcon, QAction, QFontDatabase, QCursor

from bus import Bus

from media_player_widget import MediaPlayerWidget
from chat import ChatOverlay
from img_tags import ImageTagger
from settings_ui import SettingsWindow
from metronome import Metronome

from theme import THEME


# Global Font Loading Helper
def load_application_fonts():
    font_path = os.path.join("ui_resources", "Nasalization.ttf")
    if os.path.exists(font_path):
        res = QFontDatabase.addApplicationFont(font_path)
        if res == -1:
            print(f"Warning: Failed to load font: {font_path}")
    else:
        print(f"Warning: Font file not found: {font_path}")


# THEME is now imported from theme.py


GLOBAL_QSS = rf"""
QMainWindow {{ background-color: {THEME["black"]}; margin: 0px; padding: 0px;}}
QWidget#CentralWidget {{ background-color: {THEME["black"]}; }}
QWidget#TitleBar {{ background-color: {THEME["ui_primary"]}; }}

/* Buttons */

QPushButton {{ 
    background-color: {THEME["ui_secondary"]}; 
    color: {THEME["ui_text"]}; 
    border: 1px solid {THEME["ui_secondary_hover"]}; 
    padding: 10px 15px; 
    border-radius: 6px; 
    font-size: 14px;
    font-weight: 500;
}}

/* TitleBar Buttons - Override Defaults (Flat, no border/radius) */
QPushButton#min_btn, 
QPushButton#max_btn, 
QPushButton#restore_btn, 
QPushButton#close_btn,
QPushButton#menu_btn,
QPushButton#min_btn:hover,
QPushButton#max_btn:hover,
QPushButton#restore_btn:hover,
QPushButton#close_btn:hover,
QPushButton#menu_btn:hover,
QPushButton#min_btn:pressed,
QPushButton#max_btn:pressed,
QPushButton#restore_btn:pressed,
QPushButton#close_btn:pressed,
QPushButton#menu_btn:pressed {{
    border: none;
    border-radius: 0px;
    padding: 0px;
}}
QPushButton#menu_btn {{ 
    background-image: url(ui_resources/hamburger.png);
}}
QPushButton#menu_btn:hover {{
    background-image: url(ui_resources/hamburger_hover.png);
}}
QPushButton#min_btn {{ 
    background-image: url(ui_resources/minimize_qt.png);
}} 
QPushButton#min_btn:hover {{ 
    background-image: url(ui_resources/minimize_qt_hover.png);
}}
QPushButton#close_btn {{ 
    background-image: url(ui_resources/close_qt.png);
}} 
QPushButton#close_btn:hover {{ 
    background-image: url(ui_resources/close_qt_hover.png);
}}
QPushButton:hover {{ 
    background-color: {THEME["ui_secondary_hover"]}; 
}}

/* ScrollBars */
QScrollBar:vertical {{
    border: none;
    background: {THEME["hero_shadow"]};
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {THEME["ui_secondary"]};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {THEME["ui_secondary_hover"]};
}}

/* Drawer Buttons - Specialized */
#DrawerButton {{
    text-align: left;
    padding-left: 20px;
    background: transparent;
    border: none;
    border-radius: 0px;
    height: 45px;
    color: {THEME["ui_text"]};
}}
#DrawerButton:hover {{
    background-color: {THEME["ui_secondary_hover"]};
    color: {THEME["highlighted"]};
}}

/* Personality Flyout Menu */
QMenu#PersonalityMenu {{
    background-color: {THEME["ui_secondary"]};
    border: 1px solid {THEME["ui_secondary_border"]};
    border-radius: 6px;
    padding: 4px 0px;
    color: {THEME["ui_text"]};
    font-size: 13px;
}}
QMenu#PersonalityMenu::item {{
    padding: 8px 20px 8px 14px;
    border-radius: 4px;
    margin: 2px 4px;
}}
QMenu#PersonalityMenu::item:selected {{
    background-color: {THEME["ui_secondary_hover"]};
    color: {THEME["highlighted"]};
}}
QMenu#PersonalityMenu::item:pressed {{
    background-color: {THEME["highlighted_shadow"]};
    color: {THEME["highlighted"]};
}}

QLabel {{ color: {THEME["ui_text"]}; }}
"""


class PersonalityFlyoutButton(QPushButton):
    """A drawer button that shows a hover-activated flyout listing Scripts/ subdirectories."""

    def __init__(self, parent=None):
        super().__init__("Select Personality  \u25b6", parent)
        self.setObjectName("DrawerButton")
        self._active_menu = None

        # Delay before showing the flyout on hover
        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.setInterval(150)
        self._show_timer.timeout.connect(self._show_flyout)

        # Polls cursor position while the flyout is open.
        # Avoids relying on leaveEvent/enterEvent which are unreliable
        # when a QMenu popup is grabbing input focus.
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(80)
        self._poll_timer.timeout.connect(self._poll_hover)

    def _get_personalities(self):
        scripts_dir = os.path.join(APPLICATION_ROOT, "Scripts")
        if not os.path.isdir(scripts_dir):
            return []
        return sorted(
            entry.name
            for entry in os.scandir(scripts_dir)
            if entry.is_dir()
        )

    def enterEvent(self, event):
        # Only start the show timer when no menu is currently open
        if self._active_menu is None:
            self._show_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Cancel pending show; actual close is handled by the poll timer
        self._show_timer.stop()
        super().leaveEvent(event)

    def _poll_hover(self):
        """Close the flyout if the cursor has left both the button and the menu."""
        cursor_pos = QCursor.pos()
        over_button = self.rect().contains(self.mapFromGlobal(cursor_pos))
        over_menu = (
            self._active_menu is not None
            and self._active_menu.isVisible()
            and self._active_menu.rect().contains(
                self._active_menu.mapFromGlobal(cursor_pos)
            )
        )
        if not over_button and not over_menu:
            self._close_menu()

    def _close_menu(self):
        self._poll_timer.stop()
        if self._active_menu is not None:
            self._active_menu.close()
            self._active_menu = None

    def _show_flyout(self):
        if self._active_menu is not None:
            return

        personalities = self._get_personalities()
        if not personalities:
            return

        # Get the currently active personality for the checkmark
        d = {}
        Bus.emit("get_current_personality", d)
        current = d.get("personality", "")

        menu = QMenu(self)
        menu.setObjectName("PersonalityMenu")
        menu.setStyleSheet(self.window().styleSheet())

        for name in personalities:
            action = QAction(name, menu)
            action.setCheckable(True)
            action.setChecked(name == current)
            action.triggered.connect(lambda checked=False, n=name: self._select_personality(n))
            menu.addAction(action)

        # Clean up when the menu closes for any reason (click-outside, Escape, etc.)
        menu.aboutToHide.connect(self._on_menu_hidden)
        self._active_menu = menu

        # Position flush to the right edge of the NavDrawer at this button's Y
        drawer = self.parent()
        global_pos = drawer.mapToGlobal(QPoint(drawer.width(), self.y()))
        menu.popup(global_pos)

        # Start polling — leaveEvent is unreliable after popup() grabs input
        self._poll_timer.start()

    def _on_menu_hidden(self):
        """Called when the menu closes for any reason — cleans up state."""
        self._poll_timer.stop()
        self._active_menu = None
        # Defer the hover-state clear: the popup close event can itself
        # interfere with Windows hover tracking, leaving the button stuck.
        # Waiting 60ms lets Qt settle before we force a re-evaluation.
        QTimer.singleShot(60, self._clear_stale_hover)

    def _clear_stale_hover(self):
        """Force-clear the :hover state if the cursor is no longer over this button."""
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def _select_personality(self, name):
        Bus.emit("set_personality", name)
        self._close_menu()
        drawer = self.parent()
        if hasattr(drawer, "close_drawer"):
            drawer.close_drawer()


class NavDrawer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavDrawer")
        self.setFixedWidth(0)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet(
            f"#NavDrawer {{ background-color: {THEME['ui_secondary']}; border-right: 1px solid {THEME['ui_secondary_hover']}; }}"
        )

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Drawer Content (Buttons)
        btn_personality = PersonalityFlyoutButton(self)

        btn_start = QPushButton("Start Session")
        btn_start.clicked.connect(lambda: Bus.emit("start"))

        btn_tagger = QPushButton("Image Tagger")
        btn_tagger.clicked.connect(lambda: Bus.emit("open_tagger"))

        btn_settings = QPushButton("User Settings")
        btn_settings.clicked.connect(lambda: Bus.emit("open_settings"))

        # Re-using the DrawerContent styles from QSS
        for btn in [btn_personality, btn_start, btn_tagger, btn_settings]:
            btn.setObjectName("DrawerButton")
            self.layout.addWidget(btn)

        self.layout.addStretch()

        # Animation
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutQuint)

        self.animation_max = QPropertyAnimation(self, b"maximumWidth")
        self.animation_max.setDuration(300)
        self.animation_max.setEasingCurve(QEasingCurve.OutQuint)

    def open_drawer(self):
        Bus.emit("pause_session")
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(175)
        self.animation_max.setStartValue(self.width())
        self.animation_max.setEndValue(175)
        self.animation.start()
        self.animation_max.start()

    def close_drawer(self):
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(0)
        self.animation_max.setStartValue(self.width())
        self.animation_max.setEndValue(0)
        self.animation.start()
        self.animation_max.start()
        Bus.emit("resume_session")

    def toggle(self):
        if self.width() < 10:
            self.open_drawer()
        else:
            self.close_drawer()


class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WA_StyledBackground)
        self.layout = QHBoxLayout(self)
        self.setFixedHeight(43)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.menu_btn = QPushButton()
        self.menu_btn.setObjectName("menu_btn")
        self.menu_btn.setFixedSize(43, 43)
        self.menu_btn.clicked.connect(self.parent.drawer.toggle)
        self.layout.addWidget(self.menu_btn)

        self.title = QLabel("TeaseAI")
        self.title.setStyleSheet("font-family: Nasalization; font-weight: bold; color: #d7d8d7; font-size: 15px;")
        self.layout.addStretch()
        self.layout.addWidget(self.title)
        self.layout.addStretch()

        self.min_btn = QPushButton()
        self.min_btn.setObjectName("min_btn")
        self.min_btn.setFixedSize(43, 43)
        self.min_btn.clicked.connect(self.parent.showMinimized)

        self.max_style = "QPushButton#max_btn { background-image: url(ui_resources/maximize_qt.png);} QPushButton#max_btn:hover { background-image: url(ui_resources/maximize_qt_hover.png);}"
        self.restore_style = "QPushButton#max_btn { background-image: url(ui_resources/restore_qt.png);} QPushButton#max_btn:hover { background-image: url(ui_resources/restore_qt_hover.png);}"
        self.max_btn = QPushButton()
        self.max_btn.setObjectName("max_btn")
        self.max_btn.setStyleSheet(self.restore_style if self.parent.isMaximized() else self.max_style)
        self.max_btn.setFixedSize(43, 43)
        self.max_btn.clicked.connect(self.on_maximize_press)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("close_btn")
        self.close_btn.setFixedSize(43, 43)
        self.close_btn.clicked.connect(self.parent.close)

        self.layout.addWidget(self.min_btn)
        self.layout.addWidget(self.max_btn)
        self.layout.addWidget(self.close_btn)

        self.start_pos = None

    def on_maximize_press(self, event):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.max_btn.setStyleSheet(self.max_style)
        else:
            self.parent.showMaximized()
            self.max_btn.setStyleSheet(self.restore_style)

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
        # Ensure fonts are loaded before styling
        load_application_fonts()

        self.setWindowFlags(Qt.FramelessWindowHint)

        # Sizing relative to screen (accounting for OS scaling)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(screen.width() * 0.7, screen.height() * 0.7)

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

        # Navigation Drawer (at the edge)
        self.drawer = NavDrawer()

        # Title Bar
        self.title_bar = TitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        # Content Layout
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.main_layout.addLayout(self.content_layout)

        self.content_layout.addWidget(self.drawer)

        # Main Page Container (for Media/Chat with margins)
        self.page_container = QWidget()
        self.page_layout = QHBoxLayout(self.page_container)
        self.page_layout.setContentsMargins(15, 15, 20, 0)
        self.page_layout.setSpacing(15)
        self.content_layout.addWidget(self.page_container)

        # Content Stack (Media Player / Settings)
        self.content_stack = QStackedWidget()

        self.media_player = MediaPlayerWidget()
        self.content_stack.addWidget(self.media_player)  # Index 0

        self.page_layout.addWidget(self.content_stack, stretch=7)

        # Chat Overlay
        self.chat = ChatOverlay()
        self.chat.setFixedWidth(400)

        # Wrapper layout to retain bottom margin for chat while media is flush
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(0, 0, 0, 15)
        self.chat_layout.addWidget(self.chat)

        self.page_layout.addLayout(self.chat_layout, stretch=3)

        # System Tray
        self.setup_tray()

        # Bus Events
        self.register_events()

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
        Bus.register("open_tagger", self._open_tagger)
        Bus.register("open_settings", self._open_settings)

    def _on_drawer_animation_finished(self):
        # We can clean this up or keep it if we need other callbacks
        pass

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
            # Disconnect the original close behavior that destroys/hides the top-level widget
            self.settings_window.btn_close.clicked.disconnect()
            self.settings_window.btn_close.clicked.connect(self._close_settings)
            self.content_stack.addWidget(self.settings_window)  # Index 1

        self.content_stack.setCurrentWidget(self.settings_window)

    def _close_settings(self):
        self.content_stack.setCurrentWidget(self.media_player)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
