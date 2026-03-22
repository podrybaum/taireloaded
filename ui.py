from kivy import Config

Config.set("kivy", "kivy_clock", "interrupt")

import ctypes
import threading
import os

import pystray

from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image
from kivymd.app import Clock, MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from PIL import Image as PILImage
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.modules import inspector
from kivymd.uix.label import MDLabel
from kivy.uix.widget import Widget

from bus import Bus
from media_player_widget import MediaPlayerWidget
from message_classes import DommeMessage, UserMessage
from img_tags import ImageTagger, TAI_MDButton
from draggable_title_bar import DraggableTitleBar
from settings_ui import Settings_UI

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


class MyDrawer(MDNavigationDrawer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.width = 150
        self.duration_open = 0.2
        self.duration_close = 0.2
        self.easing = "in_out_cubic"

    def set_state(self, new_state="toggle", animation=True):
        super().set_state(new_state, animation)
        if self.state == "open" or self.status in ("opening_with_animation", "opening_with_swipe"):
            self.width = 150
            self._update_drawer_width()

    def _update_drawer_width(self):
        self.width = 150


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hwnd = user32.GetForegroundWindow()
        self.layout = RelativeLayout()
        title = DraggableTitleBar()
        self.layout.add_widget(title)
        self.drawer = MyDrawer(radius=[0, 24, 24, 0], pos_hint={"left": 0}, state="close", width=150)
        drawer_content = BoxLayout(orientation="vertical", size_hint=(1, None))
        self.select_personality = MDButton(
            MDButtonText(text="Select Personality"), style="text", size_hint_x=1, pos_hint={"center_x": 0.5}
        )
        self.select_personality.bind(on_release=self.on_select_personality)
        drawer_content.add_widget(self.select_personality)
        start = MDButton(MDButtonText(text="Start"), style="text", size_hint_x=1, pos_hint={"center_x": 0.5})
        start.bind(on_release=lambda *args: Bus.emit("start"))
        drawer_content.add_widget(start)
        tag_images = MDButton(MDButtonText(text="Tag Images"), style="text", size_hint_x=1, pos_hint={"center_x": 0.5})
        self.tagger = ImageTagger(size_hint=(None, None), size=(1000, 774))
        tag_images.bind(on_release=lambda *args: Window.add_widget(self.tagger))
        drawer_content.add_widget(tag_images)
        self.setting_ui = Settings_UI(size_hint=(None, None), size=(1000, 774))
        settings_button = MDButton(
            MDButtonText(text="Settings"), style="text", size_hint_x=1, pos_hint={"center_x": 0.5}
        )
        settings_button.bind(on_release=lambda *args: Window.add_widget(self.settings_ui))
        drawer_content.add_widget(settings_button)

        self.drawer.add_widget(drawer_content)
        self.layout.add_widget(self.drawer)
        self.drawer_handle = Image(
            source="ui_resources\\handle.png",
            size_hint=(None, None),
            size=(28, 64),
            pos_hint={"center_y": 0.5},
            opacity=0.7,
        )
        self.layout.add_widget(self.drawer_handle)
        self.media_player = MediaPlayerWidget(
            pos_hint={"center_y": 0.5, "right": 0.65},
            size_hint=(None, None),
            size=(self.layout.width * 0.6, self.layout.height * 0.8),
        )
        self.layout.add_widget(self.media_player)

        self.chat_overlay = MDBoxLayout(
            orientation="vertical",
            padding=16,
            spacing=8,
            size_hint=(0.3, 0.9),
            pos_hint={"center_y": 0.5, "right": 0.98},
            radius=[24, 24, 24, 24],
            md_bg_color=(0.12, 0.12, 0.15),
        )
        self.chat_scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4),
            bar_color=(0.5, 0.5, 0.5, 0.5),
            bar_inactive_color=(0.5, 0.5, 0.5, 0.3),
            effect_cls="ScrollEffect",
        )
        self.chat_messages = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(12), padding=[0, dp(8), 0, dp(8)]
        )
        self.chat_messages.bind(minimum_height=self.chat_messages.setter("height"))

        self.chat_spacer = Widget(size_hint_y=None, height=0)
        self.chat_messages.add_widget(self.chat_spacer)

        def update_spacer(*args):
            content_h = sum(c.height for c in self.chat_messages.children if c != self.chat_spacer)
            content_h += len(self.chat_messages.children) * dp(12)
            new_h = max(0, self.chat_scroll.height - content_h)
            self.chat_spacer.height = new_h

        self.chat_scroll.bind(height=update_spacer)
        self.chat_messages.bind(minimum_height=update_spacer)

        self.chat_scroll.add_widget(self.chat_messages)
        self.chat_overlay.add_widget(self.chat_scroll)

        self.input_field = MDTextField(
            MDTextFieldHintText(text="Type a message"),
            mode="outlined",
            multiline=False,
            size_hint_y=None,
            height=60,
            radius=[20, 20, 20, 20],
        )
        self.input_field.bind(on_text_validate=self.send_user_message)
        self.chat_overlay.add_widget(self.input_field)
        self.layout.add_widget(self.chat_overlay)
        self.input_field.focus = True
        Window.bind(mouse_pos=self._on_mouse_pos)
        self.add_widget(self.layout)

        def update_layout(*args):
            self.media_player.width = self.layout.width * 0.68 - (self.layout.width * 0.05 + self.drawer_handle.width)
            self.media_player.height = self.layout.height * 0.8

        self.layout.bind(width=update_layout)
        self.layout.bind(height=update_layout)

        def sync_handle_position(*args):
            initial = self.drawer_handle.right
            self.drawer_handle.x = self.drawer.x + self.drawer.width
            delta = self.drawer_handle.right - initial
            self.media_player.x += delta
            self.media_player.width -= delta

        self.drawer.bind(
            x=sync_handle_position,
            width=sync_handle_position,
            open_progress=sync_handle_position,
            state=sync_handle_position,
            status=sync_handle_position,
        )
        Bus.register("new_message", self.on_new_message)
        Bus.register("new_script_error", self.raise_script_error)
        Bus.register("clear_chat", self.on_clear_chat)
        Window.bind(on_key_down=lambda w, key, *largs: self.minimize_to_tray() if key == 286 else None)
        inspector.create_inspector(Window, self)
        update_layout()

        Window.borderless = True
        Window.size = (1280, 720)
        Window.left = 0
        Window.top = 0
        Window.clearcolor = (0.08, 0.08, 0.10, 1)

    def on_select_personality(self, *args):
        _, names, _ = next(os.walk(os.path.join(APPLICATION_ROOT, "Scripts")))
        personality_picker = Widget(
            size_hint=(None, None),
            x=self.select_personality.x + 150,
            y=self.select_personality.to_window(self.select_personality.x, self.select_personality.y)[1],
        )
        personality_picker.layout = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            x=self.select_personality.x + 150,
            y=self.select_personality.to_window(self.select_personality.x, self.select_personality.y)[1],
        )

        def personality_button(name):
            Bus.emit("set_personality", name)
            Window.remove_widget(personality_picker)

        for name in names:
            button = TAI_MDButton(text=name)
            button.radius = 0
            button.bind(on_press=lambda *args: personality_button(name))
            personality_picker.layout.add_widget(button)
        personality_picker.add_widget(personality_picker.layout)
        personality_picker.size = (dp(100), dp(50) * (len(names) - 1))
        personality_picker.layout.size = (dp(100), dp(50) * (len(names)))
        Window.add_widget(personality_picker)

    def on_clear_chat(self):
        self.chat_messages.children = self.chat_messages.children[-1]

    def on_new_message(self, message):
        if isinstance(message, DommeMessage):
            return self.domme_is_typing(message)
        self.post_message(message)
        if isinstance(message, UserMessage):
            Clock.schedule_once(lambda _: Bus.emit("new_message", DommeMessage("D", "testing")), 1)

    def post_message(self, message):
        self.chat_messages.add_widget(message, index=0)

        def scroll_bottom(*args):
            self.chat_scroll.scroll_y = 0

        Clock.schedule_once(scroll_bottom, 0)
        Clock.schedule_once(scroll_bottom, 0.1)
        self.input_field.focus = True
        if len(self.chat_messages.children) > 51:
            self.chat_messages.remove_widget(self.chat_messages.children[-2])

    def domme_is_typing(self, message):
        """Show animated typing, then reveal real message after delay"""
        Bus.emit("rapid_text_setting_requested", rt := {})
        if rt["rt"] is True:
            return
        self.typing_label = MDLabel(
            text=f"{message.sender} is typing", padding=(dp(0), dp(0), dp(0), dp(10)), size_hint_y=None
        )
        self.typing_label.bind(texture_size=lambda s, t: setattr(s, "height", t[1] + dp(10)))
        self.post_message(self.typing_label)

        def animate_ellipses(_):
            if self.typing_label.text.endswith("."):
                name, dots = self.typing_label.text.split(" is typing")
                dots = len(dots)
            else:
                name = self.typing_label.text.split()[0]
                dots = 0
            self.typing_label.text = name + " is typing" + "." * ((dots % 3) + 1)

        self.typing_anim = Clock.schedule_interval(animate_ellipses, 0.5)
        delay = max(3, len(message.text) * 0.05)

        Clock.schedule_once(self.remove_typing_indicator, delay)
        Clock.schedule_once(lambda _: self.post_message(message), delay + 0.05)

    def remove_typing_indicator(self, _):
        if hasattr(self, "typing_anim"):
            self.typing_anim.cancel()
        self.chat_messages.remove_widget(self.typing_label)

    def raise_script_error(self, error):
        label = MDLabel(text=error, md_bg_color=("#d43650"), text_color=(1, 1, 1, 1), size_hint=(0.95, None))
        label.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        label.bind(texture_size=lambda s, t: setattr(s, "height", t[1]))
        self.post_message(label)

    def send_user_message(self, *args):
        Bus.emit("new_message", UserMessage(self.input_field.text))
        self.input_field.text = ""
        self.input_field.focus = True

    def minimize_to_tray(self):
        user32.ShowWindow(self.hwnd, 0)
        image = PILImage.open("ui_resources/tray_icon.png")
        menu = pystray.Menu(
            pystray.MenuItem("Restore", self.restore_from_tray),
            pystray.MenuItem("Exit", lambda: MDApp.get_running_app().stop()),
        )
        icon = pystray.Icon("TeaseAI", image, "TeaseAI", menu)

        def run_tray():
            icon.run()

        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()

    def restore_from_tray(self, icon=None):
        user32.ShowWindow(self.hwnd, 5)
        if icon:
            icon.stop()

    def _on_mouse_pos(self, window, pos):
        if pos[0] < 28 and self.drawer.state == "close":
            self.drawer.set_state("open")
        elif pos[0] > self.drawer.width and self.drawer.state == "open":
            self.drawer.set_state("close")


class TeaseAIApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.material_style = "M3"
        return MainScreen()


if __name__ == "__main__":
    TeaseAIApp().run()
