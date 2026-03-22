from kivy.core.audio import SoundLoader
from kivymd.app import Clock
from bus import Bus


class Metronome:
    def __init__(self):
        self.metro_click = SoundLoader.load("ui_resources/metro_click.mp3")
        self.metro_click2 = SoundLoader.load("ui_resources/metro_click3.mp3")
        self.tempo = 30
        self.clock = None
        self.i = 0
        Bus.register("stroke_faster", self.faster)
        Bus.register("stroke_slower", self.slower)
        Bus.register("stroke_fastest", self.fastest)
        Bus.register("stroke_slowest", self.slowest)
        Bus.register("start_stroking", self.play)
        Bus.register("stop_stroking", self.stop)
        Bus.register("metro_start", self.play)
        Bus.register("metro_stop", self.stop)
        Bus.register("get_metro_pace", self._on_get_pace)

    def _on_get_pace(self, dict):
        dict["pace"] = self.tempo

    def pattern_1(self, *args):
        Clock.schedule_once(lambda dt: self.metro_click.play(), 60 / self.tempo - self.metro_click.length)
        Clock.schedule_once(lambda dt: self.metro_click2.play(), 120 / self.tempo - self.metro_click2.length)
        Clock.schedule_once(
            lambda dt: self.metro_click.play(), 120 / self.tempo + 30 / self.tempo - self.metro_click.length
        )
        Clock.schedule_once(
            lambda dt: self.metro_click.play(), 120 / self.tempo + 60 / self.tempo - self.metro_click.length
        )
        Clock.schedule_once(
            lambda dt: self.metro_click.play(), 120 / self.tempo + 90 / self.tempo - self.metro_click.length
        )
        Clock.schedule_once(
            self.pattern_1,
            120 / self.tempo + 90 / self.tempo - self.metro_click.length + 60 / self.tempo - self.metro_click.length,
        )

    def faster(self):
        self.tempo += 20
        if self.tempo >= 120:
            self.tempo = 120

    def fastest(self, *args):
        self.tempo = 120

    def slower(self):
        self.tempo -= 20
        if self.tempo <= 30:
            self.tempo = 30

    def slowest(self):
        self.tempo = 30

    def play(self, *args):
        clicks = [self.metro_click, self.metro_click2]
        clicks[self.i].play()
        self.clock = Clock.schedule_once(self.play, (60 / self.tempo) - clicks[self.i].length)
        self.i += 1
        if self.i == len(clicks):
            self.i = 0

    def stop(self, *args):
        self.metro_click.stop()
        self.clock.cancel()
