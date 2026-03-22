from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.core.audio import SoundLoader
from kivymd.app import Clock
from metronome import Metronome
import random
from slideshow import Slideshow, URL_File
from tai_exceptions import RuntimeErr
from cv2 import CAP_PROP_FPS, VideoCapture, imwrite
import os

# TODO: possibly replace cv2 with imageio for better performance

from bus import Bus

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


class MediaPlayerWidget(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_widget = Image(size_hint=(1, 1), fit_mode="contain", anim_delay=0.08, mipmap=True)
        self.add_widget(self.image_widget)
        self.url_file = None
        self.slideshow = Slideshow()
        self.video_widget = Video(size_hint=(1, 1), fit_mode="contain", opacity=0)
        self.video_widget.bind(eos=lambda: Bus.emit("video_eos"))
        self.active_sounds = {}
        self.metronome = Metronome()
        self.fps = 30
        self.frames = []
        self.pointer = 0
        self.slow_motion = False

        Bus.register("video_eos", self._on_video_eos)
        Bus.register("play_video", self._on_play_video)
        Bus.register("pause_video", self._on_pause_video)
        Bus.register("stop_video", self._on_stop_video)
        Bus.register("seek_video", self._on_seek_video)

        Bus.register("play_audio", self._on_play_audio)
        Bus.register("play_audio_loop", self._on_play_audio_loop)
        Bus.register("stop_audio", self._on_stop_audio)
        Bus.register("wait_audio", self._on_wait_audio)

        Bus.register("show_image", self._on_show_image)
        Bus.register("hide_image", self._on_hide_image)
        Bus.register("get_video_info", self._get_video_info)
        Bus.register("unpause_video", self._on_unpause_video)
        Bus.register("get_slowmo_state", self._on_get_slowmo_state)
        Bus.register("start_slowmo", self._on_start_slowmo)

        Bus.register("show_blog_image", self._on_show_blog_image)

        #Bus.emit("show_blog_image")

    def _on_start_slowmo(self):
        self.slow_motion = True
        self.fps = self.fps / 2

    def _on_get_slowmo_state(self, dict):
        dict["slowmo"] = self.slow_motion

    def _on_video_eos(self):
        pass  # TODO?

    def _on_show_blog_image(self):
        settings = {"offline_mode": False}
        Bus.emit("offline_mode_setting_requested", settings)
        if settings["offline_mode"] is True:
            Bus.emit("next_slide")
            return
        if self.url_file is None:
            if len(os.listdir("url_files")) == 0:
                RuntimeErr("You have no URL files configured, and a script is trying to access a URL file.  Configure a URL file in settings.").throw()
            file = random.choice(os.listdir("url_files"))
            self.url_file = URL_File.from_json(file)
            self.url_file.load()
        self.image_widget.texture = random.choice(self.slideshow.slides).img.texture

    def get_video_frames(self, source):
        vid = VideoCapture(source)
        count, success = 0, True
        while success:
            # left pad the count with 0s to preserve order
            if len(str(count)) < 4:
                diff = 4 - len(str(count))
                for _ in range(diff):
                    count = str(0) + str(count)

            success, image = vid.read()
            if success:
                imwrite(os.path.join(APPLICATION_ROOT, f"ui_resources\\cumshots\\frame{count}.jpg"), image)
                count = int(count) + 1

            self.fps = vid.get(CAP_PROP_FPS)

        vid.release()
        self.frames = os.listdir(os.path.join(APPLICATION_ROOT, "ui_resources\\cumshots\\"))

    def play_from_frames(self, dt):
        fps = self.fps / 2 if self.slow_motion else self.fps
        if self.pointer == len(self.frames):
            return
        self.image_widget.source = os.path.join(APPLICATION_ROOT, "ui_resources\\cumshots\\", self.frames[self.pointer])
        self.pointer += 1
        # with kivy's clock set to "interrupt", frame deltas are very consistent (on my machine) at -0.0055
        # so it appears we can simply adjust for the delta to pretty faithfully reproduce the original
        # framerate.
        Clock.schedule_once(self.play_from_frames, (1 / fps) + dt)

    def _on_play_video(self, source, duration=None):
        if self.slow_motion is True:
            self.frames = self.get_video_frames(source)
            return self.play_from_frames(0)
        if self.video_widget is not None:
            self.video_widget.unload()
            self.video_widget = None
        self.image_widget.opacity = 0
        if duration is not None:
            self.video_widget = Video(
                source=source, duration=duration, size_hint=(1, 1), state="play", fit_mode="contain"
            )
        else:
            self.video_widget = Video(source=source, size_hint=(1, 1), state="play", fit_mode="contain")
        self.add_widget(self.video_widget)

    def _on_unpause_video(self):
        if self.video_widget:
            self.video_widget.state = "play"

    def _on_pause_video(self, *args):
        if self.video_widget:
            self.video_widget.state = "pause"

    def _on_stop_video(self, *args):
        if self.video_widget:
            self.remove_widget(self.video_widget)
            self.video_widget.unload()
            self.video_widget = None

    def _on_seek_video(self, percent, relative=False, *args):
        if self.video_widget and self.video_widget.duration:
            if relative:
                current_percent = self.video_widget.position / self.video_widget.duration
                self.video_widget.seek(max(0.0, min(1.0, current_percent + percent)))
            else:
                self.video_widget.seek(max(0.0, min(1.0, percent)))

    def _on_play_audio(self, source, *args):
        sound = SoundLoader.load(source)
        if sound:
            sound.play()
            self.active_sounds[source] = sound
            sound.bind(on_stop=self._on_stop_audio)

    def _on_play_audio_loop(self, source, delay=0, *args):
        sound = SoundLoader.load(source)
        if sound:
            sound.play()
            if delay > 0:

                def play_again(*_):
                    Clock.schedule_once(lambda dt: sound.play(), delay)

                sound.bind(on_stop=play_again)
            self.active_sounds[source] = sound

    def _on_stop_audio(self, source=None, *args):
        if source:
            sound = self.active_sounds.pop(source, None)
            if sound:
                sound.stop()
                sound.unload()
        else:
            for s in list(self.active_sounds.values()):
                s.stop()
                s.unload()
            self.active_sounds.clear()

    def _on_wait_audio(self, dict):
        remaining = 0
        if len(self.active_sounds) > 0:
            for sound in list(self.active_sounds.values()):
                if sound.length - sound.get_pos() > remaining:
                    remaining = sound.length - sound.get_pos()
        dict["remaining"] = remaining

    def _on_show_image(self, source, *args):
        if self.video_widget:
            self._on_stop_video()
        self.image_widget.source = source
        self.image_widget.opacity = 1

    def _on_hide_image(self, *args):
        self.image_widget.opacity = 0
        self.image_widget.source = ""

    def _get_video_info(self, result_dict, *args):
        if self.video_widget:
            result_dict["duration"] = getattr(self.video_widget, "duration", 0)
            result_dict["position"] = getattr(self.video_widget, "position", 0)
            result_dict["state"] = getattr(self.video_widget, "state", "stop")
        else:
            result_dict["duration"] = 0
            result_dict["position"] = 0
            result_dict["state"] = "stop"
