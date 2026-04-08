import os
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QFrame
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Slot, QPoint, Property, QUrl, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView

from bus import Bus
from message_classes import get_chat_css, get_message_html, UserMessage, DommeMessage, SystemMessage, EmoteMessage


class FloatLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._font_size = 14
        self._is_floating = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.update_style()

    def update_style(self, floating=None):
        if floating is not None:
            self._is_floating = floating
        bg = (
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #373737, stop:0.60 #373737, stop:0.61 #2d2d2d, stop:1 #2d2d2d);"
            if self._is_floating
            else "background: #2d2d2d;"
        )
        self.setStyleSheet(f"font-size: {self._font_size}px; color: #b683f6; {bg} padding: 0 4px;")
        self.adjustSize()

    @Property(int)
    def fontSize(self):
        return self._font_size

    @fontSize.setter
    def fontSize(self, size):
        self._font_size = size
        self.update_style()

    def set_text(self, text):
        self.setText(text)
        self.adjustSize()


class MaterialInput(QWidget):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: transparent;")

        self.container = QFrame(self)
        self.container.setObjectName("InputContainer")
        self.container.setGeometry(0, 20, 400, 40)
        self.container.setStyleSheet("""
            #InputContainer {
                border: 1px solid #624d7d;
                border-radius: 12px;
                background-color: #2d2d2d;
            }
        """)

        self.edit = QLineEdit(self.container)
        self.edit.setFrame(False)
        self.edit.setStyleSheet("background: transparent; color: white; padding: 0;")
        self.edit.setGeometry(10, 5, 380, 30)

        self.label = FloatLabel(placeholder, self)
        self.label.move(12, 30)

        self.pos_anim = QPropertyAnimation(self.label, b"pos")
        self.pos_anim.setDuration(200)
        self.pos_anim.setEasingCurve(QEasingCurve.OutQuint)

        self.size_anim = QPropertyAnimation(self.label, b"fontSize")
        self.size_anim.setDuration(200)

        self.edit.focusInEvent = self._on_focus_in
        self.edit.focusOutEvent = self._on_focus_out
        self.edit.textChanged.connect(self._check_text)

    def resizeEvent(self, event):
        self.container.setFixedWidth(self.width())
        self.edit.setFixedWidth(self.width() - 20)
        super().resizeEvent(event)

    def _on_focus_in(self, event):
        self._animate_up()
        QLineEdit.focusInEvent(self.edit, event)

    def _on_focus_out(self, event):
        if not self.edit.text():
            self._animate_down()
        QLineEdit.focusOutEvent(self.edit, event)

    def _check_text(self):
        if self.edit.text():
            self._animate_up()

    def _animate_up(self):
        if self.label.y() > 20:
            self.label.update_style(floating=True)
            self.pos_anim.setEndValue(QPoint(12, 12))
            self.size_anim.setEndValue(11)
            self.pos_anim.start()
            self.size_anim.start()

    def _animate_down(self):
        if self.label.y() < 25 and not self.edit.hasFocus():
            self.label.update_style(floating=False)
            self.pos_anim.setEndValue(QPoint(12, 30))
            self.size_anim.setEndValue(14)
            self.pos_anim.start()
            self.size_anim.start()

    def text(self):
        return self.edit.text()

    def clear(self):
        self.edit.clear()

    def setFocus(self):
        self.edit.setFocus()

    def set_temp_placeholder(self, text):
        self._og_placeholder = getattr(self, "_og_placeholder", self.label.text())
        self.label.set_text(text)

    def restore_placeholder(self):
        if hasattr(self, "_og_placeholder"):
            self.label.set_text(self._og_placeholder)


class ChatOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatOverlay")
        self.setAttribute(Qt.WA_StyledBackground)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(0)

        # WebEngineView for the chat background
        self.webview = QWebEngineView()
        self.webview.setAttribute(Qt.WA_TranslucentBackground)
        self.webview.page().setBackgroundColor(Qt.transparent)
        self.webview.setStyleSheet("background: transparent; border-radius: 12px;")
        self.webview.setContextMenuPolicy(Qt.NoContextMenu)

        # Initial HTML content
        base_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>{get_chat_css()}</style>
            <script>
                function appendMessage(html) {{
                    const container = document.body;
                    const indicator = document.getElementById("typing-indicator");
                    if (indicator) {{
                        indicator.insertAdjacentHTML('beforebegin', html);
                    }} else {{
                        container.insertAdjacentHTML('beforeend', html);
                    }}
                    setTimeout(() => {{ window.scrollTo(0, document.body.scrollHeight); }}, 20);
                }}
                function showTyping(senderName) {{
                    removeTyping();
                    const html = `
                    <div id="typing-indicator" class="message-row">
                        <div class="msg-content" style="align-items: flex-start; margin-left: 20px;">
                            <div class="bubble" style="background: transparent; box-shadow: none; font-style: italic; opacity: 0.8; padding: 2px; color: #808080;">
                                <b>${{senderName}}</b> <span id="typing-text">is typing</span>
                            </div>
                        </div>
                    </div>`;
                    document.body.insertAdjacentHTML('beforeend', html);
                    setTimeout(() => {{ window.scrollTo(0, document.body.scrollHeight); }}, 20);
                }}
                function updateTyping(dots) {{
                    const el = document.getElementById("typing-text");
                    if (el) {{
                        el.innerText = `is typing${{dots}}`;
                    }}
                }}
                function removeTyping() {{
                    const el = document.getElementById("typing-indicator");
                    if (el) el.remove();
                }}
            </script>
        </head>
        <body>
        </body>
        </html>
        """
        base_url = QUrl.fromLocalFile(os.getcwd() + os.path.sep)
        self.webview.setHtml(base_html, base_url)
        self.layout.addWidget(self.webview)

        # Input Field Container (Float at bottom)
        self.input_field = MaterialInput("Type a message")
        self.input_field.edit.returnPressed.connect(self.send_message)

        self.layout.addWidget(self.input_field)

        self.setStyleSheet("""
            #ChatOverlay {
                background-color: #373737;
                border-radius: 12px;
            }
            QLabel {
                background: transparent;
                color: #e0e0e0;
            }
        """)

        self.wait_timer = QTimer(self)
        self.wait_timer.timeout.connect(self._wait_tick)
        self.wait_duration = 0

        self.typing_queue = []
        self._is_typing = False
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self._typing_finished)
        self.typing_timer.setSingleShot(True)
        self.dots_timer = QTimer(self)
        self.dots_timer.timeout.connect(self._animate_typing_dots)
        self.dots_count = 0

        self.register_events()

    def register_events(self):
        Bus.register("show_input_cue", self._on_show_input_cue)
        Bus.register("hide_input_cue", self._on_hide_input_cue)
        Bus.register("show_wait_ui", self._on_show_wait_ui)
        Bus.register("hide_wait_ui", self._on_hide_wait_ui)
        Bus.register("clear_chat", self._on_clear_chat)

    @Slot()
    def _on_clear_chat(self):
        self.webview.page().runJavaScript("document.body.innerHTML = '';")

    def _on_show_input_cue(self, *args):
        self.input_field.set_temp_placeholder("Waiting for user input...")
        if not self.input_field.edit.hasFocus():
            # If not focused, pop it up so the user sees the new text.
            self.input_field._animate_up()

    def _on_hide_input_cue(self, *args):
        self.input_field.restore_placeholder()
        if not self.input_field.edit.hasFocus() and not self.input_field.edit.text():
            self.input_field._animate_down()

    def _on_show_wait_ui(self, duration):
        self.wait_duration = duration
        self._update_wait_text()
        self.wait_timer.start(1000)
        self.input_field._animate_up()

    def _wait_tick(self):
        self.wait_duration -= 1
        self._update_wait_text()
        if self.wait_duration <= 0:
            self._on_hide_wait_ui()

    def _on_hide_wait_ui(self, *args):
        self.wait_timer.stop()
        self._on_hide_input_cue()

    def _update_wait_text(self):
        self.input_field.set_temp_placeholder(f"Script paused for {self.wait_duration} seconds...")

    def send_message(self):
        text = self.input_field.text().strip()
        if text:
            from message_classes import UserMessage

            Bus.emit("new_message", UserMessage(text=text))
            self.input_field.clear()

    @Slot(object)
    def post_message(self, message):
        from utils import get_runtime

        if isinstance(message, UserMessage):
            Bus.emit("new_message", DommeMessage(get_runtime().active_domme, "Testing"))

        # Determine msg_type and extract text/sender
        if isinstance(message, (UserMessage, DommeMessage, SystemMessage, EmoteMessage)):
            sender = getattr(message, "sender", "You")
            text = getattr(message, "text", "")
            msg_type = message.__class__.__name__.lower().replace("message", "")
        else:
            text = getattr(message, "text", str(message))
            sender = getattr(message, "sender", "You")
            if str(sender).lower() in ["you", "user"]:
                msg_type = "user"
            else:
                msg_type = "domme"

        if msg_type in ["domme", "emote"]:
            self.typing_queue.append((sender, text, msg_type))
            if not self._is_typing:
                self._process_next_typing()
        else:
            self._display_message(sender, text, msg_type)

    def _display_message(self, sender, text, msg_type):
        html = get_message_html(sender, text, msg_type)
        js_code = f"appendMessage({json.dumps(html)});"
        self.webview.page().runJavaScript(js_code)

    def _process_next_typing(self):
        if not self.typing_queue:
            self._is_typing = False
            return

        self._is_typing = True
        sender, text, msg_type = self.typing_queue[0]

        delay = min(6000, 1000 + len(text) * 45)

        js_code = f"showTyping({json.dumps(sender)});"
        self.webview.page().runJavaScript(js_code)

        self.dots_count = 0
        self.dots_timer.start(400)
        self.typing_timer.start(delay)

    def _animate_typing_dots(self):
        self.dots_count = (self.dots_count + 1) % 4
        dots = "." * self.dots_count
        js_code = f"updateTyping({json.dumps(dots)});"
        self.webview.page().runJavaScript(js_code)

    def _typing_finished(self):
        self.dots_timer.stop()
        js_code = "removeTyping();"
        self.webview.page().runJavaScript(js_code)

        sender, text, msg_type = self.typing_queue.pop(0)
        self._display_message(sender, text, msg_type)
        Bus.emit("interpreter_ready")

        self._process_next_typing()
