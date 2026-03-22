from datetime import datetime

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.metrics import dp
from kivymd.uix.label import MDLabel


class ChatMessage(BoxLayout):
    def __init__(self, sender="", text=""):
        super().__init__()
        self.sender = str(sender)
        self.text = text
        self.orientation = "horizontal"
        self.avatar_image = sender._avatar if hasattr(sender, "_avatar") else None
        self.size_hint_y = None
        self.spacing = dp(0)
        self.padding = [dp(0), dp(0), dp(0), dp(0)]
        self.timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.msg_container = BoxLayout(orientation="vertical", spacing=dp(0), padding=dp(0), size_hint=(0.85, None))
        self.msg_container.bind(minimum_height=self.msg_container.setter("height"))

        self.name_label = MDLabel(
            text=f"{self.sender} said:",
            halign="left",
            theme_text_color="Primary",
            font_size="10sp",
            size_hint_y=None,
            padding=(0, 0),
        )
        self.name_label.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        self.name_label.bind(texture_size=lambda s, t: setattr(s, "height", t[1]))
        self.msg_container.add_widget(self.name_label)

        self.bubble_text = MDLabel(
            text=self.text,
            halign="left",
            valign="top",
            padding=(dp(12), dp(12), dp(12), dp(12)),
            font_size="12sp",
            md_bg_color=(0.5, 0.5, 0.5, 1),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
        )
        self.bubble_text.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        self.bubble_text.bind(texture_size=lambda s, t: setattr(s, "height", t[1]))
        self.msg_container.add_widget(self.bubble_text)

        timestamp_label = MDLabel(
            text=self.timestamp,
            halign="right",
            theme_text_color="Primary",
            font_size="10sp",
            size_hint_y=None,
            padding=(0, 0),
        )
        timestamp_label.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        timestamp_label.bind(texture_size=lambda s, t: setattr(s, "height", t[1]))
        self.msg_container.add_widget(timestamp_label)

        self.avatar_container = BoxLayout(
            orientation="vertical", spacing=dp(0), padding=dp(0), width=32, size_hint=(None, 1)
        )
        self.avatar = Image(source=self.avatar_image, size=(32, 32), size_hint=(None, None))
        self.spacer = MDLabel(size_hint=(None, 1))

    def finish_init(self, msg_type):
        """
        Finish initializing the chat message UI element.

        Parameters:
            msg_type (str): The type of message to be displayed. Can be either "domme" or "user".
        """
        if self.avatar_image is None:
            self.avatar.source = "ui_resources\\user_avatar.png"
        if msg_type == "domme":
            self.bubble_text.radius = [dp(0), dp(16), dp(16), dp(16)]
            self.bubble_text.md_bg_color = (0.1, 0.3, 0.6, 1)  # Muted Deep Blue for Domme
            self.avatar_container.add_widget(self.avatar)
            self.avatar_container.add_widget(self.spacer)
            self.add_widget(self.avatar_container)
            self.add_widget(self.msg_container)
        if msg_type == "user":
            self.bubble_text.radius = [dp(16), dp(16), dp(0), dp(16)]
            self.bubble_text.md_bg_color = (0.2, 0.2, 0.25, 1)  # Dark Indigo/Grey for User
            self.avatar_container.add_widget(self.spacer)
            self.avatar_container.add_widget(self.avatar)
            self.add_widget(self.msg_container)
            self.add_widget(self.avatar_container)
            # Add an explicit spacer on the far right to give room from the scrollbar
        pad_spacer = MDLabel(size_hint_x=None, width=dp(12))
        self.add_widget(pad_spacer)
        self.bind(minimum_height=self.setter("height"))


class DommeMessage(ChatMessage):
    def __init__(self, sender, text=""):
        super().__init__(sender, text)
        self.finish_init("domme")


class UserMessage(ChatMessage):
    def __init__(self, text=""):
        self.sender = "You"
        super().__init__(self.sender, text)
        self.finish_init("user")


class SystemMessage(BoxLayout):
    def __init__(self, text=""):
        super().__init__()
        self.orientation = "horizontal"
        self.padding = [dp(0), dp(0), dp(0), dp(0)]

        label = MDLabel(
            text=f"System Message: {text}",
            halign="left",
            theme_text_color="Custom",
            text_color=(0.5, 0.5, 0.5, 1),
            font_size="14sp",
            italic=True,
            markup=True,
            size_hint_y=None,
            pos_hint={"center_y": 0},
        )
        label.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        label.bind(texture_size=lambda s, t: setattr(s, "height", t[1]))
        self.add_widget(label)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))


class EmoteMessage(BoxLayout):
    def __init__(self, sender, text):
        super().__init__()
        self.sender = sender.name
        self.orientation = "horizontal"
        self.padding = [dp(0), dp(0), dp(0), dp(0)]

        label = MDLabel(
            text=f"*{self.sender} {text}*",
            halign="left",
            theme_text_color="Custom",
            text_color=(0.5, 0.5, 0.5, 1),
            font_size="14sp",
            italic=True,
            markup=True,
            size_hint_y=None,
            pos_hint={"center_y": 0},
        )
        label.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        label.bind(texture_size=lambda s, t: setattr(s, "height", t[1]))
        self.add_widget(label)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))
