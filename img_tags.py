import os
from pathlib import Path
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.modules import inspector

from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, RoundedRectangle
from kivymd.app import MDApp
from kivymd.uix.button import MDFabButton, MDButtonText, MDButton
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList, MDListItem, MDListItemHeadlineText, MDListItemLeadingIcon
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.widget import MDWidget
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogSupportingText, MDDialogButtonContainer

from bus import Bus
from utils import is_image_file
from draggable_title_bar import DraggableTitleBar


class FileBrowserDropdown(BoxLayout):
    def __init__(self, tagger, **kwargs):
        super().__init__(**kwargs)
        self.tagger = tagger
        self.orientation = "vertical"
        with self.canvas.before:
            Color(0.06, 0.05, 0.06, 1.0)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(1, 1, 1, 0.15)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1)
        self.bind(pos=self.update_rect, size=self.update_rect)
        self.scroll = MDScrollView()
        self.wrapper = BoxLayout(orientation="vertical", size_hint_y=None)
        self.list = MDList(size_hint_y=None)
        self.list.bind(minimum_height=self.list.setter("height"))
        self.spacer = Widget(size_hint_y=1)
        self.wrapper.add_widget(self.list)
        self.wrapper.add_widget(self.spacer)

        def _update_wrapper_height(*args):
            self.wrapper.height = max(self.scroll.height, self.list.minimum_height)
            if self.list.minimum_height >= self.scroll.height:
                self.spacer.size_hint_y = None
                self.spacer.height = 0
            else:
                self.spacer.size_hint_y = 1

        self.scroll.bind(height=_update_wrapper_height)
        self.list.bind(minimum_height=_update_wrapper_height)
        self.scroll.add_widget(self.wrapper)
        self.add_widget(self.scroll)
        self.bottom_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), padding=[dp(10), dp(5)])
        self.bottom_bar.add_widget(Widget(size_hint_x=1))
        self.confirm_btn = TAI_MDButton(text="Confirm", md_bg_color=(0.3, 0.3, 0.4, 1))
        self.confirm_btn.bind(on_press=lambda *args: Bus.emit("tag_dir_selected"))
        self.bottom_bar.add_widget(self.confirm_btn)
        self.add_widget(self.bottom_bar)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(8))

    def open(self, path):
        path = os.path.abspath(path)
        self.list.clear_widgets()
        parent_path = os.path.abspath(os.path.join(path, os.pardir))
        if parent_path and parent_path != path:
            item = MDListItem(MDListItemLeadingIcon(icon="folder-upload"), MDListItemHeadlineText(text=".."))
            item.bind(on_release=lambda x, p=parent_path: self.tagger.select_path(p))
            self.list.add_widget(item)
        try:
            items = os.listdir(path)
        except (PermissionError, FileNotFoundError, OSError):
            items = []
        dirs = []
        for item in items:
            if item.startswith("."):
                continue
            try:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    dirs.append(item)
            except OSError:
                pass
        dirs.sort(key=str.casefold)
        for d in dirs:
            full_path = os.path.join(path, d)
            item = MDListItem(MDListItemLeadingIcon(icon="folder"), MDListItemHeadlineText(text=d))
            item.bind(on_release=lambda x, p=full_path: self.tagger.select_path(p))
            self.list.add_widget(item)


class TAI_MDButton(ButtonBehavior, MDLabel):
    def __init__(self, **kwargs):
        MDLabel().__init__(**kwargs)
        super().__init__()
        self.text = kwargs["text"]
        self.height = dp(40)
        self.font_size = "16sp"
        self.halign = "center"
        self.theme_bg_color = "Custom"
        self.md_bg_color = "#221e25"
        self.radius = 8
        self.size_hint = (None, None)
        self.width = dp(100)
        self.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.bind(on_enter=self.on_enter, on_leave=self.on_leave)

    def on_enter(self, *args):
        self.md_bg_color = "#332d36"

    def on_leave(self, *args):
        self.md_bg_color = "#221e25"


class SectionBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.after:
            Color(1, 1, 1, 0.15)
            self.rect = Line(width=1, rectangle=(self.x, self.y, self.width, self.height))
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.rectangle = (self.x, self.y, self.width, self.height)


class SectionGridLayout(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.after:
            Color(1, 1, 1, 0.15)
            self.rect = Line(width=1, rectangle=(self.x, self.y, self.width, self.height))
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.rectangle = (self.x, self.y, self.width, self.height)


class CheckboxControl(BoxLayout):
    def __init__(self, text):
        super().__init__()
        self.orientation = "horizontal"
        self.size_hint_x = 1
        self.checkbox = MDCheckbox(size_hint_x=0.1)
        self._active = False
        self.checkbox.bind(active=lambda inst, val: setattr(self, "_active", val))
        self.add_widget(self.checkbox)
        self.label = MDLabel(
            text=text,
            halign="left",
            font_size="12sp",
            pos_hint={"center_y": 0.4},
            theme_text_color="Custom",
            text_color=[0.65, 0.65, 0.65, 1],
        )
        self.text = self.label.text.replace(" ", "")
        self.add_widget(self.label)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        self._active = value
        self.checkbox.active = value  # pushes the change into the actual UI widget


class ImageTagger(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#000000"
        self.layout = BoxLayout(orientation="vertical", size_hint=(1, 1), pos_hint={"center_x": 0.5, "center_y": 0.5})
        title_bar = DraggableTitleBar(controls=False, draggable_target=self)
        title_bar.title_label.text = "Image Tagger"
        self.layout.add_widget(title_bar)
        row1 = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(62), padding=dp(10), spacing=dp(5))
        self.file_browser = FileBrowserDropdown(tagger=self, size_hint=(1, 1))
        self.manager_open = False

        self.filepicker = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=5,
        )

        self.file_input = MDTextField(
            text="Select images directory",
            text_color_normal=[0.6, 0.6, 0.6, 1],
            text_color_focus=[0.6, 0.6, 0.6, 1],
            disabled=True,
            mode="outlined",
            size_hint=(1, None),
            height=dp(42),
            font_size="14sp",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=[dp(12), dp(10), dp(12), dp(10)],
        )

        file_button = MDFabButton(
            icon="folder-image",
            style="small",
            on_press=self.file_manager_open,
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=0,
            theme_bg_color="Custom",
            md_bg_color="#221e25",
        )

        inspector.create_inspector(Window, self)

        self.filepicker.add_widget(self.file_input)
        self.filepicker.add_widget(file_button)
        row1.add_widget(self.filepicker)

        number_widget = BoxLayout(
            orientation="horizontal",
            size_hint=(None, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=5,
        )

        number_widget.bind(minimum_width=number_widget.setter("width"))
        left_arrow = MDFabButton(
            icon="arrow-left",
            style="small",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            theme_bg_color="Custom",
            md_bg_color="#221e25",
        )
        left_arrow.bind(on_press=self._go_back)

        self.number_field = MDTextField(
            text="0 / 0",
            mode="outlined",
            size_hint=(None, None),
            height=dp(38),
            halign="center",
            width=dp(100),
            font_size="16sp",
            padding=[dp(12), dp(10), dp(12), dp(2)],
            text_color_normal=[0.6, 0.6, 0.6, 1],
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            disabled=True,
        )

        right_arrow = MDFabButton(
            icon="arrow-right",
            style="small",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            theme_bg_color="Custom",
            md_bg_color="#221e25",
        )
        right_arrow.bind(on_press=self._go_forward)
        number_widget.add_widget(left_arrow)
        number_widget.add_widget(self.number_field)
        number_widget.add_widget(right_arrow)
        row1.add_widget(number_widget)

        finish_box = BoxLayout(
            orientation="horizontal",
            size_hint=(None, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=0,
        )

        finish_box.bind(minimum_width=finish_box.setter("width"))
        finished_button = TAI_MDButton(text="Finished")
        finished_button.bind(on_release=self._save_and_exit)
        finish_box.add_widget(finished_button)
        row1.add_widget(finish_box)
        self.layout.add_widget(row1)
        row2 = BoxLayout(orientation="horizontal", size_hint=(1, 1), pos_hint={"center_x": 0.5, "center_y": 0.5})
        category = SectionBoxLayout(
            orientation="vertical",
            size_hint=(0.9, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=5,
        )
        category_header = MDLabel(text="Category", halign="left", font_size="18sp", bold=True)
        category.add_widget(category_header)
        hardcore = CheckboxControl("Hardcore")
        category.add_widget(hardcore)
        lesbian = CheckboxControl("Lesbian")
        category.add_widget(lesbian)
        gay = CheckboxControl("Gay")
        category.add_widget(gay)
        bisexual = CheckboxControl("Bisexual")
        category.add_widget(bisexual)
        solof = CheckboxControl("Solo F")
        category.add_widget(solof)
        solom = CheckboxControl("Solo M")
        category.add_widget(solom)
        solo_futa = CheckboxControl("Solo Futa")
        category.add_widget(solo_futa)
        POV = CheckboxControl("POV")
        category.add_widget(POV)
        Bondage = CheckboxControl("Bondage")
        category.add_widget(Bondage)
        s_and_m = CheckboxControl("S&M")
        category.add_widget(s_and_m)
        t_and_d = CheckboxControl("T&D")
        category.add_widget(t_and_d)
        chastity = CheckboxControl("Chastity")
        category.add_widget(chastity)
        cfnm = CheckboxControl("CFNM")
        category.add_widget(cfnm)
        bath = CheckboxControl("Bath")
        category.add_widget(bath)
        shower = CheckboxControl("Shower")
        category.add_widget(shower)
        outdoors = CheckboxControl("Outdoors")
        category.add_widget(outdoors)
        artwork = CheckboxControl("Artwork")
        category.add_widget(artwork)
        row2.add_widget(category)
        sex = SectionBoxLayout(
            orientation="vertical",
            size_hint=(1.2, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=5,
        )

        sex_header = MDLabel(text="Sex", halign="left", font_size="18sp", bold=True)
        sex.add_widget(sex_header)

        masturbation = CheckboxControl("Masturbation")
        sex.add_widget(masturbation)

        handjob = CheckboxControl("Handjob")

        sex.add_widget(handjob)

        fingering = CheckboxControl("Fingering")
        sex.add_widget(fingering)

        blowjob = CheckboxControl("Blowjob")

        sex.add_widget(blowjob)

        cunnilingus = CheckboxControl("Cunnilingus")
        sex.add_widget(cunnilingus)

        titjob = CheckboxControl("Titjob")

        sex.add_widget(titjob)

        footjob = CheckboxControl("Footjob")

        sex.add_widget(footjob)

        facesitting = CheckboxControl("Facesitting")
        sex.add_widget(facesitting)

        rimming = CheckboxControl("Rimming")
        sex.add_widget(rimming)

        missionary = CheckboxControl("Missionary")

        sex.add_widget(missionary)

        doggystyle = CheckboxControl("Doggystyle")

        sex.add_widget(doggystyle)

        cowgirl = CheckboxControl("Cowgirl")
        sex.add_widget(cowgirl)

        reverse_cowgirl = CheckboxControl("Reverse Cowgirl")

        sex.add_widget(reverse_cowgirl)

        standing = CheckboxControl("Standing")
        sex.add_widget(standing)

        anal = CheckboxControl("Anal Sex")
        sex.add_widget(anal)

        dp_checkbox = CheckboxControl("DP")
        sex.add_widget(dp_checkbox)

        gangbang = CheckboxControl("Gangbang")
        sex.add_widget(gangbang)

        row2.add_widget(sex)

        genders_and_roles = SectionBoxLayout(
            orientation="vertical",
            size_hint=(1.1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=5,
        )

        genders_and_roles_header = MDLabel(text="Genders & Roles", halign="left", font_size="18sp", bold=True)
        genders_and_roles.add_widget(genders_and_roles_header)

        one_woman = CheckboxControl("1 Woman")
        genders_and_roles.add_widget(one_woman)

        two_women = CheckboxControl("2 Women")
        genders_and_roles.add_widget(two_women)

        three_women = CheckboxControl("3 Women")
        genders_and_roles.add_widget(three_women)

        one_man = CheckboxControl("1 Man")
        genders_and_roles.add_widget(one_man)

        two_men = CheckboxControl("2 Men")
        genders_and_roles.add_widget(two_men)

        three_men = CheckboxControl("3 Men")
        genders_and_roles.add_widget(three_men)

        one_futa = CheckboxControl("1 Futa")
        genders_and_roles.add_widget(one_futa)

        two_futa = CheckboxControl("2 Futa")
        genders_and_roles.add_widget(two_futa)

        three_futa = CheckboxControl("3 Futa")
        genders_and_roles.add_widget(three_futa)

        femdom = CheckboxControl("Femdom")
        genders_and_roles.add_widget(femdom)

        maledom = CheckboxControl("Maledom")
        genders_and_roles.add_widget(maledom)

        futadom = CheckboxControl("Futadom")
        genders_and_roles.add_widget(futadom)

        femsub = CheckboxControl("Femsub")
        genders_and_roles.add_widget(femsub)

        malesub = CheckboxControl("Malesub")
        genders_and_roles.add_widget(malesub)

        futasub = CheckboxControl("Futasub")
        genders_and_roles.add_widget(futasub)

        multi_dom = CheckboxControl("Multi-Dom")
        genders_and_roles.add_widget(multi_dom)

        multi_sub = CheckboxControl("Multi-Sub")
        genders_and_roles.add_widget(multi_sub)

        row2.add_widget(genders_and_roles)

        col4 = BoxLayout(
            orientation="vertical",
            size_hint=(0.9, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=0,
            spacing=10,
        )

        body_parts = SectionBoxLayout(
            orientation="vertical",
            size_hint=(1, 0.65),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=5,
        )

        body_parts_header = MDLabel(text="Body Parts", halign="left", font_size="18sp", bold=True)

        body_parts.add_widget(body_parts_header)

        face = CheckboxControl("Face")

        body_parts.add_widget(face)

        fingers = CheckboxControl("Fingers")

        body_parts.add_widget(fingers)

        mouth = CheckboxControl("Mouth")

        body_parts.add_widget(mouth)

        tits = CheckboxControl("Tits")

        body_parts.add_widget(tits)

        nipples = CheckboxControl("Nipples")

        body_parts.add_widget(nipples)

        pussy = CheckboxControl("Pussy")

        body_parts.add_widget(pussy)

        ass = CheckboxControl("Ass")

        body_parts.add_widget(ass)

        legs = CheckboxControl("Legs")

        body_parts.add_widget(legs)

        feet = CheckboxControl("Feet")

        body_parts.add_widget(feet)

        cock = CheckboxControl("Cock")

        body_parts.add_widget(cock)

        balls = CheckboxControl("Balls")

        body_parts.add_widget(balls)

        col4.add_widget(body_parts)

        outfit = SectionBoxLayout(
            orientation="vertical",
            size_hint=(1, 0.35),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=5,
            spacing=5,
        )

        outfit_header = MDLabel(text="Outfit", halign="left", font_size="18sp", bold=True)
        outfit.add_widget(outfit_header)

        Nurse = CheckboxControl("Nurse")

        outfit.add_widget(Nurse)

        Teacher = CheckboxControl("Teacher")

        outfit.add_widget(Teacher)

        Schoolgirl = CheckboxControl("Schoolgirl")

        outfit.add_widget(Schoolgirl)

        Maid = CheckboxControl("Maid")

        outfit.add_widget(Maid)

        Superhero = CheckboxControl("Superhero")

        outfit.add_widget(Superhero)

        col4.add_widget(outfit)

        row2.add_widget(col4)
        col5 = BoxLayout(
            orientation="vertical",
            size_hint=(2.1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=0,
            spacing=10,
        )
        col5_upper = BoxLayout(orientation="horizontal", size_hint=(1, 0.65), padding=0, spacing=5)
        bdsm = SectionBoxLayout(
            orientation="vertical", size_hint=(1, 1), pos_hint={"center_x": 0.5, "center_y": 0.5}, padding=5, spacing=5
        )

        bdsm_header = MDLabel(text="BDSM", halign="left", font_size="18sp", bold=True)
        bdsm.add_widget(bdsm_header)

        Whipping = CheckboxControl("Whipping")

        bdsm.add_widget(Whipping)

        Spanking = CheckboxControl("Spanking")

        bdsm.add_widget(Spanking)

        Cock_Torture = CheckboxControl("Cock Torture")

        bdsm.add_widget(Cock_Torture)

        Ball_Torture = CheckboxControl("Ball Torture")

        bdsm.add_widget(Ball_Torture)

        Strap_On = CheckboxControl("Strap-On")

        bdsm.add_widget(Strap_On)

        Blindfold = CheckboxControl("Blindfold")

        bdsm.add_widget(Blindfold)

        Gag = CheckboxControl("Gag")

        bdsm.add_widget(Gag)

        Clamps = CheckboxControl("Clamps")
        bdsm.add_widget(Clamps)

        Hot_Wax = CheckboxControl("Hot Wax")

        bdsm.add_widget(Hot_Wax)

        Needles = CheckboxControl("Needles")

        bdsm.add_widget(Needles)

        Electro = CheckboxControl("Electro")

        bdsm.add_widget(Electro)
        col5_upper.add_widget(bdsm)
        misc = SectionBoxLayout(orientation="vertical", size_hint=(1, 1), padding=0, spacing=5)
        misc_header = MDLabel(text="Misc", halign="left", font_size="18sp", bold=True)
        misc.add_widget(misc_header)
        TAI_Domme = CheckboxControl("TAI Domme")
        misc.add_widget(TAI_Domme)
        Cumshot = CheckboxControl("Cumshot")
        misc.add_widget(Cumshot)
        Cum_Eating = CheckboxControl("Cum Eating")
        misc.add_widget(Cum_Eating)
        Kissing = CheckboxControl("Kissing")
        misc.add_widget(Kissing)
        Tattoos = CheckboxControl("Tattoos")
        misc.add_widget(Tattoos)
        Stockings = CheckboxControl("Stockings")
        misc.add_widget(Stockings)
        Vibrator = CheckboxControl("Vibrator")
        misc.add_widget(Vibrator)
        Dildo = CheckboxControl("Dildo")
        misc.add_widget(Dildo)
        Pocket_Pussy = CheckboxControl("Pocket Pussy")
        misc.add_widget(Pocket_Pussy)
        Anal_Toy = CheckboxControl("Anal Toy")
        misc.add_widget(Anal_Toy)
        Watersports = CheckboxControl("Watersports")
        misc.add_widget(Watersports)
        col5_upper.add_widget(misc)
        col5.add_widget(col5_upper)
        col5_lower_container = SectionBoxLayout(orientation="vertical", size_hint=(1, 0.35), padding=5, spacing=5)
        col5_lower_header = MDLabel(
            text="Hentai/JAV Themes", halign="left", font_size="18sp", bold=True, size_hint=(1, None), height=dp(30)
        )
        col5_lower_container.add_widget(col5_lower_header)

        col5_lower = GridLayout(cols=2, size_hint=(1, 1), padding=0, spacing=5)

        Shibari = CheckboxControl("Shibari")
        col5_lower.add_widget(Shibari)
        Body_Writing = CheckboxControl("Body Writing")
        col5_lower.add_widget(Body_Writing)
        Tentacles = CheckboxControl("Tentacles")
        col5_lower.add_widget(Tentacles)
        Trap = CheckboxControl("Trap")
        col5_lower.add_widget(Trap)
        Bukkake = CheckboxControl("Bukkake")
        col5_lower.add_widget(Bukkake)
        Gangoru = CheckboxControl("Gangoru")
        col5_lower.add_widget(Gangoru)
        Bakunyuu = CheckboxControl("Bakunyuu")
        col5_lower.add_widget(Bakunyuu)
        Mahou_Shoujo = CheckboxControl("Mahou Shoujo")
        col5_lower.add_widget(Mahou_Shoujo)
        Ahegao = CheckboxControl("Ahegao")
        col5_lower.add_widget(Ahegao)
        Monster_Girl = CheckboxControl("Monster Girl")
        col5_lower.add_widget(Monster_Girl)

        col5_lower_container.add_widget(col5_lower)
        col5.add_widget(col5_lower_container)
        row2.add_widget(col5)
        self.layout.add_widget(row2)
        self.add_widget(self.layout)

        self.fm_container = BoxLayout(orientation="vertical", size_hint=(None, None))
        self.add_widget(self.fm_container)
        Bus.register("tag_dir_selected", self._on_tag_dir_selected)
        Bus.register("go_forward", self._go_forward)
        Bus.register("go_back", self._go_back)
        Bus.register("tagger_save_and_exit", self._save_and_exit)
        self.index = 0
        self.imgs = []
        self.tags = []

        def walk_child_for_tags(child):
            for child in child.children:
                if isinstance(child, CheckboxControl):
                    self.tags.append(child)
                else:
                    walk_child_for_tags(child)

        walk_child_for_tags(self)

    def _save_and_exit(self, *args):
        self.write_tags_to_file()
        if self.parent:
            self.parent.remove_widget(self)
        else:
            MDApp.get_running_app().stop()

    def _go_back(self, *args):
        if not len(self.imgs) > 0:
            return
        self.write_tags_to_file()
        for tag in self.tags:
            tag.active = False
        self.index -= 1
        Bus.emit("show_image", os.path.join(self.folder, self.imgs[self.index]))
        self.get_tags_from_file()
        self.number_field.text = f"{self.index + 1} / {len(self.imgs)}"

    def write_tags_to_file(self):
        out_tags = []
        for tag in self.tags:
            if tag.active:
                out_tags.append(tag.text)
        new_line = self.imgs[self.index] + " " + " ".join(out_tags) + "\n" if out_tags else None
        with open(self.tag_file, "r") as f:
            lines = f.readlines()
        key = self.imgs[self.index]
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith(key):
                lines[i] = new_line if new_line else "\n"
                replaced = True
                break
        if not replaced and new_line:
            lines.append(new_line)
        with open(self.tag_file, "w") as f:
            f.writelines(lines)

    def _go_forward(self, *args):
        if not len(self.imgs) > 0:
            return
        self.write_tags_to_file()
        for tag in self.tags:
            tag.active = False
        self.index += 1
        Bus.emit("show_image", os.path.join(self.folder, self.imgs[self.index]))
        self.get_tags_from_file()
        self.number_field.text = f"{self.index + 1} / {len(self.imgs)}"

    def _on_tag_dir_selected(self, *args):
        self.index = 0
        self.folder = self.file_input.text
        if os.path.isdir(self.folder):
            self.imgs = [file for file in os.listdir(self.folder) if is_image_file(file)]
        if len(self.imgs) < 1:
            self.show_alert_dialog()
        else:
            Bus.emit("show_image", os.path.join(self.folder, self.imgs[self.index]))
            self.exit_manager()
            self.tag_file = os.path.join(self.folder, "ImageTags.txt")
            Path(self.tag_file).touch(exist_ok=True)
            self.get_tags_from_file()
            self.number_field.text = f"{self.index + 1} / {len(self.imgs)}"

    def get_tags_from_file(self):
        with open(self.tag_file, "r") as f:
            for line in f:
                if line.startswith(self.imgs[self.index]):
                    tags = line.split()[1:]
                    for tag in tags:
                        for t in self.tags:
                            if t.text == tag:
                                t.active = True

    def show_alert_dialog(self, *args):
        popup = MDDialog(
            MDDialogHeadlineText(text="No images found"),
            MDDialogSupportingText(text="Please select a folder containing valid image files."),
            MDDialogButtonContainer(
                MDWidget(),
                MDButton(MDButtonText(text="Okay"), style="text", on_press=lambda x: popup.dismiss()),
                spacing=dp(4),
            ),
            width=dp(200),
        )
        popup.open()

    def file_manager_open(self, *args):
        if self.manager_open:
            self.exit_manager()
            return

        self.fm_container.width = self.file_input.width
        self.fm_container.height = dp(400)
        self.fm_container.pos = (self.file_input.x, self.file_input.y - dp(400))

        if self.file_browser not in self.fm_container.children:
            self.fm_container.add_widget(self.file_browser)

        start_path = self.file_input.text
        if not start_path or not os.path.exists(start_path):
            start_path = os.path.expanduser("~")
            self.file_input.text = start_path

        self.file_browser.open(start_path)

        self.manager_open = True

    def select_path(self, path: str):
        self.file_input.text = path
        self.file_browser.open(path)

    def exit_manager(self, *args):
        self.manager_open = False
        if self.file_browser in self.fm_container.children:
            self.fm_container.remove_widget(self.file_browser)


class MyApp(MDApp):
    def build(self):

        self.theme_cls.primary_palette = "Indigo"

        self.theme_cls.accent_palette = "Amber"

        self.theme_cls.theme_style = "Dark"

        self.theme_cls.material_style = "M3"

        return ImageTagger()


if __name__ == "__main__":
    MyApp().run()
