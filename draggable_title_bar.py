import ctypes
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivymd.app import MDApp

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_dpi():
    hdc = user32.GetDC(0)
    dpi = gdi32.GetDeviceCaps(hdc, 88)
    user32.ReleaseDC(0, hdc)
    return dpi


def get_absolute_mouse_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)

class DraggableTitleBar(BoxLayout):
    def __init__(self, controls=True, draggable_target=None, **kwargs):
        super().__init__(**kwargs)
        # If set, dragging moves this widget's pos instead of the OS window
        self.draggable_target = draggable_target
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 24
        self.padding = [0, 0, 16, 0]
        self.spacing = 16
        self.pos_hint = {"top": 1}
        self.last_x = 0
        self.last_y = 0
        self._dragging = False
        self.maximized = False
        self._normal_left = Window.left
        self._normal_top = Window.top
        self._normal_size = Window.size
        self.title_label = Label(text="", size_hint_x=0.7, halign="left", valign="middle")
        self.add_widget(self.title_label)
        if controls:
            self.min_btn = Button(
                background_normal="ui_resources\\minimize.png",
                size_hint=(None, None),
                width=16,
                height=16,
                pos_hint={"center_y": 0.5},
            )
            self.min_btn.bind(on_release=lambda x: Window.minimize())
            self.add_widget(self.min_btn)
            self.max_btn = Button(
                background_normal="ui_resources\\maximize.png",
                size_hint=(None, None),
                width=16,
                height=16,
                pos_hint={"center_y": 0.5},
            )
            self.max_btn.bind(on_release=self.toggle_maximize)
            self.add_widget(self.max_btn)
            close = Button(
                background_normal="ui_resources\\close.png",
                size_hint=(None, None),
                width=16,
                height=16,
                pos_hint={"center_y": 0.5},
            )
            close.bind(on_release=lambda x: MDApp.get_running_app().stop())
            self.add_widget(close)

    def toggle_maximize(self, *args):
        scaling_factor = 1 / (get_dpi() / 96)
        if Window.size == self._get_work_area():
            Window.size = int(self._normal_width * scaling_factor), int(self._normal_height * scaling_factor)
            Window.left = self._normal_left
            Window.top = self._normal_top
        else:
            self._normal_left = Window.left
            self._normal_top = Window.top
            self._normal_width, self._normal_height = Window.size
            work_width, work_height = self._get_work_area()
            work_width = int(work_width * scaling_factor)
            work_height = int(work_height * scaling_factor)
            Window.size = (work_width, work_height)
            Window.left = 0
            Window.top = 0

    def _get_work_area(self):
        """Get work area of the monitor the window is currently on"""

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint32),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_uint32),
            ]

        hwnd = user32.GetForegroundWindow()
        monitor = user32.MonitorFromWindow(hwnd, 2)
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        success = user32.GetMonitorInfoA(monitor, ctypes.byref(info))
        if success:
            rect = info.rcWork
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            return (width, height)
        else:
            rect = RECT()
            user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            return (width, height)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._dragging = True
            self.last_x, self.last_y = get_absolute_mouse_pos()
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self._dragging = False
        return super().on_touch_up(touch)

    def on_touch_move(self, touch):
        if self._dragging:
            x, y = get_absolute_mouse_pos()
            dx, dy = x - self.last_x, y - self.last_y
            self.last_x, self.last_y = x, y
            if self.draggable_target is not None:
                # Move the target widget within Kivy space.
                # Screen Y is top-down, Kivy Y is bottom-up, so dy is negated.
                self.draggable_target.x += dx
                self.draggable_target.y -= dy
            else:
                Window.left += dx
                Window.top += dy
            return True  # Consume event — stop siblings from also handling it
        return super().on_touch_move(touch)
