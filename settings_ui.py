from kivymd.app import MDApp
from kivy.properties import BooleanProperty
from kivy.properties import NumericProperty
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.divider import MDDivider
from kivymd.uix.screen import MDScreen
from kivymd.uix.tab import MDTabsItemText, MDTabsSecondary, MDTabsItemSecondary
from kivy.uix.boxlayout import BoxLayout
from kivy.modules import inspector
from draggable_title_bar import DraggableTitleBar
from kivy.metrics import dp
from img_tags import CheckboxControl
from main import runtime
from kivymd.theming import ThemableBehavior
from kivymd.uix.behaviors import BackgroundColorBehavior
from kivymd.uix.behaviors.elevation import CommonElevationBehavior


SETTINGS_CONTROL_LABEL_WIDTH = dp(250)


class SettingsCheckboxControl(CheckboxControl):
    active = BooleanProperty(False)

    def __init__(self, disabled=False, **kwargs):
        self.name = kwargs.pop("name")
        self._disabled_value = disabled
        super().__init__(**kwargs)
        # Apply the specialized dp(38) layout for settings specifically
        self.size_hint = (None, None)
        self.height = dp(38)
        self.spacing = dp(5)
        self.padding = dp(5)
        self.valign = "top"

        # Override children created by CheckboxControl
        self.checkbox.size_hint = (None, None)
        self.checkbox.size = (dp(24), dp(24))
        self.checkbox.pos_hint = {"top": 1}
        self.checkbox.disabled = self._disabled_value

        self.label.size_hint = (None, None)
        self.label.width = SETTINGS_CONTROL_LABEL_WIDTH
        self.label.height = dp(24)
        self.label.font_size = 18
        self.label.text_color = "#FFFFFF" if not self.disabled else "#3D3D3D"
        self.label.pos_hint = {"top": 1}
        self.label.valign = "bottom"
        self.label.bind(size=self.label.setter("text_size"))

        # Invert order for settings
        self.remove_widget(self.checkbox)
        self.add_widget(self.checkbox)

        # Link logic
        self.checkbox.bind(active=self.setter("active"))
        self.bind(active=lambda inst, val: setattr(self.checkbox, "active", val))

    def on_active(self, instance, value):
        runtime.settings.set(self.name, value)


class NumericTextFieldEntry(BoxLayout):
    def __init__(self, name, label, value, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.label = MDLabel(text=label)
        self.value = NumericProperty(value)
        self.size_hint = (None, None)
        self.height = dp(30)
        self.spacing = dp(5)
        self.padding = dp(5)
        self.label.size_hint = (None, None)
        self.text_field = MDTextField(text=str(value))
        self.text_field.size_hint = (None, None)
        self.label.pos_hint = {"center_y": 0.5}
        self.text_field.pos_hint = {"center_y": 0.5}
        self.label.font_size = 18
        self.text_field.font_size = 14
        self.text_field.height = dp(30)
        self.add_widget(self.label)
        self.add_widget(self.text_field)
        self.label.width = SETTINGS_CONTROL_LABEL_WIDTH
        self.label.valign = "bottom"
        self.label.height = self.text_field.height
        self.text_field.width = dp(50)
        self.text_field.bind(text=self.setter("value"))

    def on_value(self, instance, value):
        runtime.settings.set(self.name, int(value))


class SettingsCard(FloatLayout, CommonElevationBehavior, ThemableBehavior, BackgroundColorBehavior):
    def __init__(self, label, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size_hint = (None, None)
        self.width = SETTINGS_CONTROL_LABEL_WIDTH + dp(77)
        self.spacing = dp(5)
        self.theme_bg_color = "Custom"
        self.md_bg_color = (0.08, 0.08, 0.1, 1)
        self.theme_line_color = "Custom"
        self.line_color = "#545454"
        self.radius = dp(8)
        # self.padding = [dp(5), dp(-5), dp(5), dp(-1)]
        self.content = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.label = MDLabel(text=f" {label}")
        self.label.theme_bg_color = "Custom"
        self.label.md_bg_color = (0, 0, 0, 1)
        self.label.size_hint = (None, None)
        self.label.theme_text_color = "Custom"
        self.label.text_color = "#545454"
        self.label.height = dp(20)
        self.label.width = dp(len(self.label.text) * dp(5))
        self.label.font_size = dp(12)
        self.label.valign = "center"
        # self.label.pos_hint = {"x": 0.05}
        poss, posy = self.to_parent(self.x, self.top)
        self.label.pos_hint = {"center_y": 1, "x": 0.05}
        self.add_widget(self.label)
        self.add_widget(self.content)

    # self.on_leave()

    # def on_enter(self, *args):
    #    return True

    def add_widget(self, *args, **kwargs):
        if len(self.children) == 2:
            self.content.add_widget(*args, **kwargs)
            self.height = self.content.height
        else:
            super().add_widget(*args)


class Settings_UI(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(1000), dp(674))
        Window.size = (1000, 674)
        self.layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.layout.bind(height=self.setter("height"))
        self.title_bar = DraggableTitleBar(controls=False, draggable_target=self, pos_hint={"top": 1})
        self.title_bar.title_label.text = "Settings"
        self.layout.add_widget(self.title_bar)
        self.tabs = MDTabsSecondary(pos_hint={"center_x": 0.5, "center_y": 0.5}, size_hint=(1, None))
        self.layout.add_widget(self.tabs)
        inspector.create_inspector(Window, self)

        self.general_settings = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(600))
        self.sub_settings = BoxLayout(
            orientation="vertical", size_hint=(1, None), height=dp(600), spacing=dp(5), padding=dp(5)
        )
        self.domme_settings = BoxLayout(orientation="vertical", size_hint=(1, None))
        self.contacts_settings = BoxLayout(orientation="vertical", size_hint=(1, None))
        self.image_folders = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=dp(10))
        self._tab_panels = {
            "General": self.general_settings,
            "Sub": self.sub_settings,
            "Domme": self.domme_settings,
            "Contacts": self.contacts_settings,
            "Image Folders": self.image_folders,
        }
        self._active_panel = self.general_settings
        self._add_tabs()
        self.tabs.bind(on_tab_switch=self.switch_tab)
        # General Settings
        domme_delete = SettingsCheckboxControl(text="Allow Domme to delete local media?", name="domme_delete")
        domme_delete.active = runtime.settings.domme_delete
        self.general_settings.add_widget(domme_delete)
        randomize_slides = SettingsCheckboxControl(text="Randomize order of image slideshows?", name="randomize_slides")
        randomize_slides.active = runtime.settings.randomize_slides
        self.general_settings.add_widget(randomize_slides)
        offline_mode = SettingsCheckboxControl(text="Offline Mode - (disables URL files )", name="offline_mode")
        offline_mode.active = runtime.settings.offline_mode
        general_sizer = BoxLayout(size_hint=(1, 1))
        self.general_settings.add_widget(offline_mode)
        self.general_settings.add_widget(general_sizer)

        # Sub Settings
        stats_box = SettingsCard(label="Stats")
        sub_age = NumericTextFieldEntry(name="Sub.age", label="Age", value=runtime.settings.Sub.age)
        stats_box.add_widget(sub_age)
        sub_cock_size = NumericTextFieldEntry(
            name="Sub.cock_size", label="Cock Size", value=runtime.settings.Sub.cock_size
        )
        stats_box.add_widget(sub_cock_size)
        self.sub_settings.add_widget(stats_box)

        sub_has_chastity = SettingsCheckboxControl(name="Sub.has_chastity", text="Owns a chastity device")
        self.sub_settings.add_widget(sub_has_chastity)
        sub_chastity_piercing = SettingsCheckboxControl(
            name="Sub.chastity_piercing", text="Chastity device requires piercing", disabled=True
        )
        self.sub_settings.add_widget(sub_chastity_piercing)
        sub_chastity_spikes = SettingsCheckboxControl(
            name="Sub.chastity_spikes", text="Chastity device has spikes", disabled=True
        )
        self.sub_settings.add_widget(sub_chastity_spikes)

        # Finish Layout Init
        self.add_widget(self.layout)
        self.switch_tab(self.tabs.children, self.tabs.children[1], "Sub")

    def _add_tabs(self, *args):
        for tab_name in ["General", "Sub", "Domme", "Contacts"]:
            self.tabs.add_widget(MDTabsItemSecondary(MDTabsItemText(text=tab_name)))
        self.tabs.add_widget(MDDivider())
        self.tabs.height = dp(50)
        self.title_bar.height = dp(24)
        self._active_panel.size_hint = (1, None)
        self._active_panel.height = dp(600)

    def switch_tab(self, instance_tabs, instance_tab, *args):
        print(args)
        if args and isinstance(args[0], str):
            instance_tab_label = args[0]
        else:
            instance_tab_label = ""
            for child in instance_tab.children:
                if isinstance(child, MDTabsItemText):
                    instance_tab_label = child.text
                    break

        print(instance_tab_label)
        panel = self._tab_panels.get(instance_tab_label)
        if panel is None or panel is self._active_panel:
            return
        self.layout.remove_widget(self._active_panel)
        self._active_panel = panel
        self.layout.add_widget(panel)
        self._active_panel = panel


class MyApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.material_style = "M3"
        return Settings_UI()


if __name__ == "__main__":
    MyApp().run()
