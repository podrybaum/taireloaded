import os
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl, QTimer, Slot, QObject
from bus import Bus

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


class Metronome(QObject):
    def __init__(self):
        super().__init__()
        # Using QSoundEffect for lower latency than QMediaPlayer for clicks
        self.metro_click = QSoundEffect(self)
        self.metro_click.setSource(QUrl.fromLocalFile(os.path.abspath("ui_resources/metro_click.mp3")))

        self.metro_click2 = QSoundEffect(self)
        self.metro_click2.setSource(QUrl.fromLocalFile(os.path.abspath("ui_resources/metro_click3.mp3")))

        self.tempo = 30
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.i = 0
        self.clicks = [self.metro_click, self.metro_click2]

        self.register_events()

    def register_events(self):
        Bus.register("stroke_faster", self.faster)
        Bus.register("stroke_slower", self.slower)
        Bus.register("stroke_fastest", self.fastest)
        Bus.register("stroke_slowest", self.slowest)
        Bus.sub("start_stroking", self.play)
        Bus.sub("stop_stroking", self.stop)
        Bus.sub("edge_start", self.fastest)
        Bus.register("metro_stop", self.stop)
        Bus.register("get_metro_pace", self._on_get_pace)

    @Slot(dict)
    def _on_get_pace(self, result_dict):
        result_dict["pace"] = self.tempo

    @Slot()
    def faster(self):
        self.tempo = min(240, self.tempo + 20)  # Match original max logic or custom
        if self.timer.isActive():
            self.play()

    @Slot()
    def fastest(self, *args):
        self.tempo = 240
        if self.timer.isActive():
            self.play()

    @Slot()
    def slower(self):
        self.tempo = max(20, self.tempo - 20)
        if self.timer.isActive():
            self.play()

    @Slot()
    def slowest(self):
        self.tempo = 30
        if self.timer.isActive():
            self.play()

    @Slot()
    def play(self, *args):
        from utils import get_runtime
        if not self.timer.isActive():
            worship_active = False
            try:
                worship_active = getattr(get_runtime(), "_worship_mode", False)
            except Exception:
                pass
            
            import random
            if worship_active:
                self.tempo = 30
            else:
                self.tempo = random.randint(60, 120) # Standard random start tempo

        # 60,000 ms / tempo = ms per beat
        interval = int(60000 / self.tempo)
        self.timer.start(interval)
        self._on_tick()

    @Slot()
    def stop(self, *args):
        self.timer.stop()

    def _on_tick(self):
        if self.clicks[self.i].status() == QSoundEffect.Ready:
            self.clicks[self.i].play()
        self.i = (self.i + 1) % len(self.clicks)
