import os
import random
import cv2
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QStackedWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, Slot, QUrl, QTimer
from PySide6.QtGui import QPixmap


from bus import Bus
from slideshow import Slideshow, URL_File
from tai_exceptions import RuntimeErr

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


class MediaPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Use QStackedWidget to switch between Image and Video
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Image Display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.current_image = None
        self.stack.addWidget(self.image_label)

        # Video Display
        self.video_widget = QVideoWidget()
        self.stack.addWidget(self.video_widget)

        # Media Player
        self.media_player = QMediaPlayer(self)
        self.media_player.setVideoOutput(self.video_widget)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        # Slideshow / URL logic
        self.url_file = None
        self.slideshow = Slideshow()

        # Slow-mo / Frame logic
        self.fps = 30
        self.frames = []
        self.pointer = 0
        self.slow_motion = False
        self.slowmo_timer = QTimer(self)
        self.slowmo_timer.timeout.connect(self._play_next_frame)

        # Audio players (source path → QMediaPlayer)
        self.active_sounds = {}

        # Overlays
        self.censor_bars = {}
        self.image_bars = {}
        self.avatar_labels = []

        self.register_events()

    def register_events(self):
        # Video Events
        Bus.register("play_video", self._on_play_video)
        Bus.register("pause_video", self._on_pause_video)
        Bus.register("stop_video", self._on_stop_video)
        Bus.register("seek_video", self._on_seek_video)
        Bus.register("unpause_video", self._on_unpause_video)
        Bus.register("video_eos", self._on_video_eos)

        # Image Events
        Bus.register("show_image", self._on_show_image)
        Bus.register("hide_image", self._on_hide_image)
        Bus.register("show_blog_image", self._on_show_blog_image)
        # Bus.register("show_image_tag", self._on_show_image_tag)
        Bus.register("get_current_image", self._on_get_current_image)
        Bus.register("show_censor_bar", self._on_show_censor_bar)
        Bus.register("hide_censor_bar", self._on_hide_censor_bar)
        Bus.register("show_image_bar", self._on_show_image_bar)
        Bus.register("hide_image_bar", self._on_hide_image_bar)
        Bus.register("set_image_bar_image", self._on_set_image_bar_image)
        Bus.register("refresh_avatars", self._on_refresh_avatars)

        # Audio Events
        Bus.register("play_audio", self._on_play_audio)
        Bus.register("play_audio_loop", self._on_play_audio_loop)
        Bus.register("stop_audio", self._on_stop_audio)
        Bus.register("wait_audio", self._on_wait_audio)

        # State Events
        Bus.register("get_video_info", self._get_video_info)
        Bus.register("get_slowmo_state", self._on_get_slowmo_state)
        Bus.register("start_slowmo", self._on_start_slowmo)

        # Session pause / resume
        Bus.register("pause_session", self._on_pause_session)
        Bus.register("resume_session", self._on_resume_session)

    # --- Session Pause / Resume ---

    def _on_pause_session(self):
        """Snapshot active playback state then pause everything."""
        self._pre_pause_video_playing = (
            self.media_player.playbackState() == QMediaPlayer.PlayingState
        )
        self._pre_pause_slowmo_active = self.slowmo_timer.isActive()
        self._pre_pause_sounds = set()

        if self._pre_pause_video_playing:
            self.media_player.pause()
        if self._pre_pause_slowmo_active:
            self.slowmo_timer.stop()
        for source, player in self.active_sounds.items():
            if player.playbackState() == QMediaPlayer.PlayingState:
                self._pre_pause_sounds.add(source)
                player.pause()

    def _on_resume_session(self):
        """Restore exactly what was playing before the pause."""
        if getattr(self, "_pre_pause_video_playing", False):
            self.media_player.play()
        if getattr(self, "_pre_pause_slowmo_active", False):
            self.slowmo_timer.start()
        for source in getattr(self, "_pre_pause_sounds", set()):
            if source in self.active_sounds:
                self.active_sounds[source].play()
        # Clear snapshot
        self._pre_pause_video_playing = False
        self._pre_pause_slowmo_active = False
        self._pre_pause_sounds = set()

    @Slot(str, object)
    def _on_play_video(self, source, duration=None):
        if self.slow_motion:
            self.get_video_frames(source)
            self.pointer = 0
            self.stack.setCurrentWidget(self.image_label)
            self.slowmo_timer.start(int(1000 / (self.fps / 2)))  # 2x slow
            return

        self.stack.setCurrentWidget(self.video_widget)
        # Handle Windows paths correctly for QUrl
        path = os.path.abspath(source)
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.media_player.play()

    @Slot(dict)
    def _on_get_current_image(self, response_dict):
        response_dict["current_image"] = self.current_image

    @Slot()
    def _on_pause_video(self, *args):
        if self.slow_motion:
            self.slowmo_timer.stop()
        else:
            self.media_player.pause()

    @Slot()
    def _on_unpause_video(self):
        if self.slow_motion:
            self.slowmo_timer.start()
        else:
            self.media_player.play()

    @Slot()
    def _on_stop_video(self, *args):
        self.media_player.stop()
        self.slowmo_timer.stop()
        self.stack.setCurrentWidget(self.image_label)

    @Slot(float, bool)
    def _on_seek_video(self, percent, relative=False, *args):
        if self.media_player.duration() > 0:
            if relative:
                current_percent = self.media_player.position() / self.media_player.duration()
                target = max(0.0, min(1.0, current_percent + percent))
            else:
                target = max(0.0, min(1.0, percent))
            self.media_player.setPosition(int(target * self.media_player.duration()))

    @Slot(str)
    def _on_show_image(self, source, *args):
        self.stack.setCurrentWidget(self.image_label)
        pixmap = QPixmap(source)
        if not pixmap.isNull():
            self.current_image = source
            self.image_label.setPixmap(
                pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.image_label.setText(f"Image not found: {source}")

    @Slot()
    def _on_hide_image(self, *args):
        self.image_label.clear()

    # --- Overlays (Censor / Image Bars / Avatars) ---

    @Slot(list)
    def _on_refresh_avatars(self, entities):
        from settings import get_settings
        
        # Cleanup old avatars
        for lbl in self.avatar_labels:
            lbl.hide()
            lbl.deleteLater()
        self.avatar_labels.clear()

        # Build new avatars
        for entity in entities:
            avatar_path = None
            if entity == "D":
                avatar_path = get_settings().Domme._avatar
            else:
                contact = getattr(get_settings(), f"Contact{entity}", None)
                if contact:
                    avatar_path = contact._avatar
            
            # Resolve relative to APP ROOT or absolute
            if avatar_path and not os.path.isabs(avatar_path):
                avatar_path = os.path.join(APPLICATION_ROOT, avatar_path)
            
            if not avatar_path or not os.path.exists(avatar_path):
                avatar_path = os.path.join(APPLICATION_ROOT, "ui_resources", "user_avatar.png")
            
            lbl = QLabel(self)
            lbl.setStyleSheet("border: 1px solid white; background-color: #222;")
            lbl.setScaledContents(True)
            if os.path.exists(avatar_path):
                pixmap = QPixmap(avatar_path)
                lbl.setPixmap(pixmap)
            
            self.avatar_labels.append(lbl)
            lbl.show()
        
        self._layout_avatars()

    def _layout_avatars(self):
        # 32x32 size, 10px spacing vertically, pinned to upper right.
        size = 32
        spacing = 10
        x = self.width() - size - spacing
        y = spacing
        for lbl in self.avatar_labels:
            lbl.setGeometry(x, y, size, size)
            y += size + spacing

    def _resolve_secure_path(self, path):
        from settings import get_settings

        path = path.lstrip("/\\")

        personality = getattr(get_settings(), "current_personality", "")
        if personality:
            pers_base = os.path.abspath(os.path.join(APPLICATION_ROOT, "Scripts", personality))
            pers_path = os.path.abspath(os.path.join(pers_base, path))
            if pers_path.startswith(pers_base) and os.path.exists(pers_path):
                return pers_path

        app_base = os.path.abspath(APPLICATION_ROOT)
        abs_path = os.path.abspath(os.path.join(app_base, path))

        if not abs_path.startswith(app_base):
            return None

        # Prevent deep traversal into other sibling directories like 'Scripts/OtherPersonality/'
        parts = os.path.relpath(abs_path, app_base).replace("\\", "/").split("/")
        if len(parts) > 2:  # i.e., ["Folder", "file.png"] is allowed, but ["Scripts", "Other", "file.png"] is blocked
            return None

        return abs_path if os.path.exists(abs_path) else None

    def _get_relative_geometry(self, x, y, w, h):
        parent_w, parent_h = self.width(), self.height()
        rx, ry = int(parent_w * (x / 800.0)), int(parent_h * (y / 600.0))
        rw, rh = int(parent_w * (w / 800.0)), int(parent_h * (h / 600.0))
        return rx, ry, rw, rh

    @Slot(int, int, int, int, int, str)
    def _on_show_censor_bar(self, num, x, y, w, h, text):
        if num not in self.censor_bars:
            lbl = QLabel(self)
            lbl.setStyleSheet("background-color: black; color: white; font-size: 16px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.censor_bars[num] = {"label": lbl, "geom": (x, y, w, h)}

        data = self.censor_bars[num]
        data["geom"] = (x, y, w, h)
        label = data["label"]
        label.setText(text)
        label.setGeometry(*self._get_relative_geometry(x, y, w, h))
        label.raise_()
        label.show()

    @Slot(int)
    def _on_hide_censor_bar(self, num):
        if num in self.censor_bars:
            self.censor_bars[num]["label"].hide()

    @Slot(int, int, int, int, int, str)
    def _on_show_image_bar(self, num, x, y, w, h, path):
        if num not in self.image_bars:
            lbl = QLabel(self)
            lbl.setStyleSheet("background-color: black;")
            lbl.setAlignment(Qt.AlignCenter)
            self.image_bars[num] = {"label": lbl, "geom": (x, y, w, h), "path": ""}

        data = self.image_bars[num]
        data["geom"] = (x, y, w, h)
        self._on_set_image_bar_image(num, path)
        data["label"].setGeometry(*self._get_relative_geometry(x, y, w, h))
        data["label"].raise_()
        data["label"].show()

    @Slot(int, str)
    def _on_set_image_bar_image(self, num, path):
        if num in self.image_bars:
            data = self.image_bars[num]
            data["path"] = path
            label = data["label"]
            resolved = self._resolve_secure_path(path)
            if resolved:
                pixmap = QPixmap(resolved)
                if not pixmap.isNull():
                    gw, gh = self._get_relative_geometry(*data["geom"])[2:4]
                    label.setPixmap(pixmap.scaled(gw, gh, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    label.setText("Image Err")
            else:
                label.setText("Path Err")

    @Slot(int)
    def _on_hide_image_bar(self, num):
        if num in self.image_bars:
            self.image_bars[num]["label"].hide()

    @Slot()
    def _on_show_blog_image(self):
        settings = {"offline_mode": False}
        Bus.emit("offline_mode_setting_requested", settings)
        if settings["offline_mode"]:
            Bus.emit("next_slide")
            return

        if self.url_file is None:
            url_dir = os.path.join(APPLICATION_ROOT, "url_files")
            if not os.path.exists(url_dir) or len(os.listdir(url_dir)) == 0:
                RuntimeErr("No URL files found.").throw()
            file = random.choice(os.listdir(url_dir))
            self.url_file = URL_File.from_json(os.path.join(url_dir, file))
            self.url_file.load()

        if self.slideshow.slides:
            slide = random.choice(self.slideshow.slides)
            self._on_show_image(slide.img_path)

    # Audio Logic
    @Slot(str)
    def _on_play_audio(self, source, *args):
        player = QMediaPlayer(self)
        audio = QAudioOutput(self)
        player.setAudioOutput(audio)
        player.setSource(QUrl.fromLocalFile(os.path.abspath(source)))
        player.play()
        self.active_sounds[source] = player

    @Slot(str, float)
    def _on_play_audio_loop(self, source, delay=0, *args):
        player = QMediaPlayer(self)
        audio = QAudioOutput(self)
        player.setAudioOutput(audio)
        player.setSource(QUrl.fromLocalFile(os.path.abspath(source)))
        player.setLoops(QMediaPlayer.Infinite if delay == 0 else 1)
        player.play()
        self.active_sounds[source] = player

    @Slot(object)
    def _on_stop_audio(self, source=None, *args):
        if source:
            p = self.active_sounds.pop(source, None)
            if p:
                p.stop()
        else:
            for p in self.active_sounds.values():
                p.stop()
            self.active_sounds.clear()

    @Slot(dict)
    def _on_wait_audio(self, result_dict):
        remaining = 0
        for p in self.active_sounds.values():
            rem = (p.duration() - p.position()) / 1000.0
            if rem > remaining:
                remaining = rem
        result_dict["remaining"] = remaining

    # Slow-mo logic
    def _on_start_slowmo(self):
        self.slow_motion = True
        self.fps = self.fps / 2

    def _on_get_slowmo_state(self, result_dict):
        result_dict["slowmo"] = self.slow_motion

    def get_video_frames(self, source):
        # Implementation of frame extraction using OpenCV (same as original)
        vid = cv2.VideoCapture(source)
        self.fps = vid.get(cv2.CAP_PROP_FPS)
        count = 0
        temp_dir = os.path.join(APPLICATION_ROOT, "ui_resources/cumshots/")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        while True:
            success, image = vid.read()
            if not success:
                break
            frame_name = f"frame{count:04d}.jpg"
            cv2.imwrite(os.path.join(temp_dir, frame_name), image)
            count += 1
        vid.release()
        self.frames = sorted(os.listdir(temp_dir))

    def _play_next_frame(self):
        if self.pointer >= len(self.frames):
            self.slowmo_timer.stop()
            return
        frame_path = os.path.join(APPLICATION_ROOT, "ui_resources/cumshots/", self.frames[self.pointer])
        self._on_show_image(frame_path)
        self.pointer += 1

    def _on_video_eos(self):
        pass

    def _get_video_info(self, result_dict, *args):
        result_dict["duration"] = self.media_player.duration() / 1000.0
        result_dict["position"] = self.media_player.position() / 1000.0
        result_dict["state"] = "play" if self.media_player.playbackState() == QMediaPlayer.PlayingState else "stop"

    def resizeEvent(self, event):
        # Refresh current image on resize to match aspect ratio
        if self.stack.currentWidget() == self.image_label and self.image_label.pixmap():
            pass  # We could re-scale here if needed
        # Re-scale active overlays directly over video
        for data in self.censor_bars.values():
            if data["label"].isVisible():
                data["label"].setGeometry(*self._get_relative_geometry(*data["geom"]))
        for num, data in self.image_bars.items():
            if data["label"].isVisible():
                data["label"].setGeometry(*self._get_relative_geometry(*data["geom"]))
                # Reset Image to scale cleanly
                self._on_set_image_bar_image(num, data["path"])
        self._layout_avatars()
        super().resizeEvent(event)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = MediaPlayerWidget()
    widget.show()
    sys.exit(app.exec())
