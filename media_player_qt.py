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

# Since Metronome uses Kivy, we'll need to port it or use a stub for now.
# For this pass, we'll focus on the Media Player itself.

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
        
        self.active_sounds = {} # Secondary sounds

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
        
        # Audio Events
        Bus.register("play_audio", self._on_play_audio)
        Bus.register("play_audio_loop", self._on_play_audio_loop)
        Bus.register("stop_audio", self._on_stop_audio)
        Bus.register("wait_audio", self._on_wait_audio)
        
        # State Events
        Bus.register("get_video_info", self._get_video_info)
        Bus.register("get_slowmo_state", self._on_get_slowmo_state)
        Bus.register("start_slowmo", self._on_start_slowmo)

    @Slot(str, object)
    def _on_play_video(self, source, duration=None):
        if self.slow_motion:
            self.get_video_frames(source)
            self.pointer = 0
            self.stack.setCurrentWidget(self.image_label)
            self.slowmo_timer.start(int(1000 / (self.fps / 2))) # 2x slow
            return

        self.stack.setCurrentWidget(self.video_widget)
        # Handle Windows paths correctly for QUrl
        path = os.path.abspath(source)
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.media_player.play()

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
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        else:
            self.image_label.setText(f"Image not found: {source}")

    @Slot()
    def _on_hide_image(self, *args):
        self.image_label.clear()

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
            pass # We could re-scale here if needed
        super().resizeEvent(event)

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = MediaPlayerWidget()
    widget.show()
    sys.exit(app.exec())
