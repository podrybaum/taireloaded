import os
import random
from datetime import datetime
from PySide6.QtCore import QTimer
from bus import Bus
from message_classes import UserMessage, DommeMessage
from utils import get_runtime, get_settings

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


class BaseTauntCycle:
    """Base class for all interval-based taunt execution modes.

    Pushes a sentinel ExecutionFrame (context="taunt") onto the interpreter's
    _stack so that @CallReturn inside taunt lines works natively. Hijacks the
    "interpreter_ready" bus signal for the duration of the cycle.

    Subclasses must implement:
        - _load_taunts() -> list[list[Block]]
        - get_interval() -> tuple[int, int]  (min_seconds, max_seconds)
        - on_cycle_end()
    """

    def __init__(self):
        self.interpreter = get_runtime()
        self.settings = get_settings()

        # Taunt pool: list of list[Block]. Each inner list is one "taunt unit."
        self.taunt_pool: list = []
        self.taunt_index: int = 0

        # The currently executing taunt's remaining blocks
        self.current_taunt: list = []

        # Whether the cycle timer has fired (used to delay on_cycle_end until
        # the current taunt finishes delivering)
        self._cycle_expired: bool = False

        # Interval timer — single-shot, fires to schedule the next taunt
        self.taunt_timer = QTimer()
        self.taunt_timer.setSingleShot(True)
        self.taunt_timer.timeout.connect(self._on_taunt_timer)

        # Build and push the sentinel frame
        self.frame = self._make_sentinel_frame()
        self.interpreter._stack.append(self.frame)
        self.interpreter._current_frame = self.frame

        # Load taunts from subclass
        self.taunt_pool = self._load_taunts()
        random.shuffle(self.taunt_pool)

    def _make_sentinel_frame(self):
        """Creates an empty ExecutionFrame with context='taunt' as a stack sentinel."""
        import importlib

        ir = importlib.import_module("interpreter rework")
        frame = ir.ExecutionFrame([], "taunt")
        frame.handler = self
        return frame

    def _load_taunts(self) -> list:
        """Override in subclass. Return a list of taunts, each taunt being a list[Block]."""
        raise NotImplementedError

    def get_interval(self) -> tuple:
        """Override in subclass. Return (min_seconds, max_seconds) for taunt interval."""
        raise NotImplementedError

    def on_cycle_end(self):
        """Override in subclass. Called when the cycle timer expires and the
        current taunt has finished delivering."""
        raise NotImplementedError

    def start(self):
        """Schedule the first taunt. interpreter.run() will no-op while our frame is on top."""
        self._schedule_next_taunt()

    def stop(self):
        """Pop sentinel frame, resume standard execution."""
        self.taunt_timer.stop()
        if self.frame in self.interpreter._stack:
            self.interpreter._stack.remove(self.frame)
        if self.interpreter._stack:
            self.interpreter._current_frame = self.interpreter._stack[-1]
            self.interpreter.run()

    def _schedule_next_taunt(self):
        min_s, max_s = self.get_interval()
        self.taunt_timer.start(random.randint(min_s, max_s) * 1000)

    def _on_taunt_timer(self):
        """Timer fired — fetch next taunt unit and begin delivering it."""
        if not self.current_taunt:
            if self.taunt_index >= len(self.taunt_pool):
                random.shuffle(self.taunt_pool)
                self.taunt_index = 0
            self.current_taunt = list(self.taunt_pool[self.taunt_index])
            self.taunt_index += 1
        self._deliver_next_block()

    def _deliver_next_block(self):
        """Execute one block then, if the taunt has more blocks, wire up interpreter_ready
        to deliver the next one. If not, schedule the next taunt interval."""
        block = self.current_taunt.pop(0)
        self.interpreter.generic_visit(block)
        if self.current_taunt:
            # More blocks remain in this taunt — deliver after chat posts the current one.
            # We temporarily sub ourselves for a single interpreter_ready, then remove
            # ourselves once the taunt unit is fully delivered.
            def _continue_taunt():
                Bus.unsub("interpreter_ready", _continue_taunt)
                self._deliver_next_block()
            Bus.sub("interpreter_ready", _continue_taunt)
        else:
            if self._cycle_expired:
                self.on_cycle_end()
            else:
                self._schedule_next_taunt()

    def output_vocab_to_chat(self, vocab: str, callback=None):
        """Emit a random line from a system vocabulary file as a DommeMessage.

        Temporarily replaces the interpreter_ready listener with `callback`
        (one-shot) so control returns to us (or caller) after the chat delay.

        Args:
            vocab: Vocabulary file base name, e.g. "#StopStroking"
            callback: Function to call on the next interpreter_ready signal.
                      If None, interpreter.run is restored immediately.
        """
        Bus.unsub("interpreter_ready", self._on_interpreter_ready)
        target = callback if callback is not None else self.interpreter.run

        def _one_shot():
            Bus.unsub("interpreter_ready", _one_shot)
            Bus.sub("interpreter_ready", self._on_interpreter_ready)
            target()

        Bus.sub("interpreter_ready", _one_shot)
        path = os.path.join(APPLICATION_ROOT, "Vocabulary", vocab + ".txt")
        with open(path, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        Bus.emit("new_message", DommeMessage(self.interpreter.active_domme, random.choice(lines)))


# ---------------------------------------------------------------------------


class StrokeTauntCycle(BaseTauntCycle):
    """Handles stroke taunt cycles (@StartStroking)."""

    TAUNT_DIRS = ["StrokeTaunts"]  # base name; _1.txt / _2.txt / _3.txt appended

    def __init__(self):
        super().__init__()
        self.interpreter._state = "stroking"
        # Cycle (tease) timer — expires to trigger on_cycle_end
        self._cycle_timer = QTimer()
        self._cycle_timer.setSingleShot(True)
        self._cycle_timer.timeout.connect(self._on_cycle_timer)
        self.start()

    def _load_taunts(self) -> list:
        pool = []
        base = os.path.join(APPLICATION_ROOT, "Scripts", self.settings.current_personality, "Stroke")
        for stride in (1, 2, 3):
            path = os.path.join(base, f"{self.TAUNT_DIRS[0]}_{stride}.txt")
            if not os.path.isfile(path):
                continue
            frame = self.interpreter.parse_script(path)
            blocks = frame.blocks
            for i in range(0, len(blocks), stride):
                chunk = blocks[i : i + stride]
                if chunk:
                    pool.append(chunk)
        return pool

    def get_interval(self) -> tuple:
        return (self.settings.taunt_cycle_min, self.settings.taunt_cycle_max)

    def start(self):
        # Start the overall stroke cycle timer
        if getattr(self.interpreter, "_worship_mode", False):
            duration = self.settings.taunt_cycle_max
        else:
            duration = random.randint(self.settings.taunt_cycle_min, self.settings.taunt_cycle_max)
        self._cycle_timer.start(duration * 1000)
        super().start()

    def stop(self):
        self._cycle_timer.stop()
        super().stop()

    def add_time(self, ms: int):
        if self._cycle_timer.isActive():
            remaining = self._cycle_timer.remainingTime()
            self._cycle_timer.start(remaining + ms)

    def remove_time(self, ms: int):
        if self._cycle_timer.isActive():
            remaining = self._cycle_timer.remainingTime()
            self._cycle_timer.start(max(1000, remaining - ms))

    def get_time(self) -> int:
        if self._cycle_timer.isActive():
            return int(self._cycle_timer.remainingTime() / 1000)
        return 0

    def _on_cycle_timer(self):
        self._cycle_expired = True

    def on_cycle_end(self):
        self.output_vocab_to_chat("#StopStroking", callback=self._finish)

    def _finish(self):
        self.interpreter._state = "chatting"
        self.stop()


class ChastityTauntCycle(StrokeTauntCycle):
    """Like StrokeTauntCycle but uses chastity taunt files and sets state to chastity_stroking."""

    TAUNT_DIRS = ["ChastityTaunts"]

    def __init__(self):
        super().__init__()
        self.interpreter._state = "chastity_stroking"


# ---------------------------------------------------------------------------


class EdgeTauntCycle(BaseTauntCycle):
    """Handles edging taunt cycles (@Edge)."""

    def __init__(self, pending_hold=None, pending_res=None, ruin_taunts=False):
        # Declare all state before super().__init__ so _load_taunts can use self.interpreter
        self.pending_edge_hold: str | None = pending_hold
        self.pending_edge_resolution: str | None = pending_res
        self.ruin_taunts_enabled: bool = ruin_taunts
        self.multiple_edges: int = 1
        self.multiple_edges_interval: int = 0

        super().__init__()
        self.interpreter._state = "edging"
        self.settings._edge_start = datetime.now()
        Bus.sub("new_message", self._on_new_message)
        self.start()

    def _load_taunts(self) -> list:
        base = os.path.join(APPLICATION_ROOT, "Scripts", self.settings.current_personality, "Stroke", "Edge")
        filename = "GroupEdge.txt" if len(self.interpreter._present) > 1 else "Edge.txt"
        path = os.path.join(base, filename)
        frame = self.interpreter.parse_script(path)
        return [[block] for block in frame.blocks]  # stride 1

    def get_interval(self) -> tuple:
        return (4, 8)

    def on_cycle_end(self):
        # Edge taunt cycle has no natural timer expiry — it's driven by user input.
        # This is a no-op here; resolution is handled in _on_new_message.
        pass

    def stop(self):
        Bus.unsub("new_message", self._on_new_message)
        super().stop()

    def _on_new_message(self, message):
        if not isinstance(message, UserMessage):
            return
        if not any(word in message.text.lower() for word in ("edge", "edging")):
            return
        self._update_edge_stats()
        self.multiple_edges -= 1

        if self.multiple_edges > 0:
            # More edges remaining — return briefly to stroking then re-edge
            self._cycle_back_to_stroking()
        elif self.pending_edge_hold is not None:
            # Last edge, but hold required before resolution
            hold = self.pending_edge_hold
            self.pending_edge_hold = None
            self.stop()
            HoldTauntCycle(hold, pending_resolution=self.pending_edge_resolution, multiple_edges_remaining=0)
        else:
            self._resolve()

    def _resolve(self):
        if self.pending_edge_resolution == "ruin":
            self.output_vocab_to_chat("#RuinYourOrgasm", callback=self._finish_ruin)
        elif self.pending_edge_resolution == "orgasm":
            self.output_vocab_to_chat("#CumForMe", callback=self._finish_orgasm)
        else:
            self.output_vocab_to_chat("#StopStroking", callback=self._finish_chatting)

    def _finish_ruin(self):
        self.interpreter.orgasm_ruined = True
        self.interpreter._state = "chatting"
        self.stop()

    def _finish_orgasm(self):
        self.interpreter.orgasm_allowed = True
        self.interpreter._state = "chatting"
        self.stop()

    def _finish_chatting(self):
        self.interpreter._state = "chatting"
        self.stop()

    def _cycle_back_to_stroking(self):
        """Between multiple edges: briefly show #StopStroking, then #StartStroking,
        wait multiple_edges_interval seconds, then fire #Edge and re-instantiate."""
        interval = self.multiple_edges_interval
        remaining = self.multiple_edges  # already decremented
        resolution = self.pending_edge_resolution
        hold = self.pending_edge_hold

        self.stop()  # hands interpreter_ready back; also unsubs new_message

        def _after_stop_stroking():
            self.interpreter._state = "chatting"

            # small wrapper to chain the next vocab output
            def _after_start_stroking():
                self.interpreter._state = "stroking"
                QTimer.singleShot(interval * 1000, _fire_edge)

            self.output_vocab_to_chat("#StartStroking", callback=_after_start_stroking)

        def _fire_edge():
            # Re-instantiate a fresh EdgeTauntCycle with remaining count and same params
            cycle = EdgeTauntCycle(pending_hold=hold, pending_res=resolution)
            cycle.multiple_edges = remaining

        self.output_vocab_to_chat("#StopStroking", callback=_after_stop_stroking)

    def _update_edge_stats(self):
        if self.settings._edge_start is None:
            return
        delta = datetime.now() - self.settings._edge_start
        self.settings.Sub._cumulative_edge_time += delta.seconds
        self.settings.Sub._edges_all_time += 1
        if self.settings.Sub._edges_all_time > 0:
            self.settings.Sub.avg_edge_time = (
                self.settings.Sub._cumulative_edge_time / self.settings.Sub._edges_all_time
            )
        self.settings._edge_start = None

    def interrupt_long_edge(self):
        """Called by Dispatch.InterruptLongEdge when long_edge_interrupts is enabled."""
        self.interpreter._state = "chatting"
        self.stop()  # unconditional — ignores multiple_edges count


# ---------------------------------------------------------------------------


class HoldTauntCycle(BaseTauntCycle):
    """Handles hold taunt cycles (post-edge hold/longhold/extremehold)."""

    def __init__(self, hold_type: str, pending_resolution=None, multiple_edges_remaining=0):
        self.hold_type: str = hold_type
        self.pending_resolution: str | None = pending_resolution
        self.multiple_edges_remaining: int = multiple_edges_remaining

        # Hold duration timer — separate from the taunt interval timer
        self.hold_timer = QTimer()
        self.hold_timer.setSingleShot(True)
        self.hold_timer.timeout.connect(self._on_hold_timer)

        super().__init__()
        self.interpreter._state = "holding"
        self._start_hold_timer()
        self.start()

    def _load_taunts(self) -> list:
        base = os.path.join(APPLICATION_ROOT, "Scripts", self.settings.current_personality, "Stroke", "Edge")
        path = os.path.join(base, "HoldTaunts.txt")
        frame = self.interpreter.parse_script(path)
        return [[block] for block in frame.blocks]

    def get_interval(self) -> tuple:
        return (4, 8)

    def _start_hold_timer(self):
        sub = self.settings.Sub
        if self.hold_type == "hold":
            duration = random.randint(sub.min_edge_hold_time, sub.max_edge_hold_time)
        elif self.hold_type == "longhold":
            duration = random.randint(sub.min_long_hold_time, sub.max_long_hold_time)
        else:  # extremehold
            duration = random.randint(sub.min_extreme_hold_time, sub.max_extreme_hold_time)
        self.hold_timer.start(duration * 1000)

    def stop(self):
        self.hold_timer.stop()
        super().stop()

    def _on_hold_timer(self):
        self._cycle_expired = True
        # If we're mid-taunt, on_cycle_end will be called after the current
        # taunt finishes. If idle, call immediately.
        if not self.current_taunt:
            self.on_cycle_end()

    def on_cycle_end(self):
        if self.multiple_edges_remaining > 0:
            remaining = self.multiple_edges_remaining
            resolution = self.pending_resolution
            self.stop()

            # Re-enter stroking -> EdgeTauntCycle path
            def _after_stop():
                self.interpreter._state = "chatting"

                def _after_start():
                    self.interpreter._state = "stroking"
                    cycle = EdgeTauntCycle(pending_res=resolution)
                    cycle.multiple_edges = remaining

                self.output_vocab_to_chat("#StartStroking", callback=_after_start)

            self.output_vocab_to_chat("#StopStroking", callback=_after_stop)
        elif self.pending_resolution == "ruin":
            self.output_vocab_to_chat("#RuinYourOrgasm", callback=self._finish_ruin)
        elif self.pending_resolution == "orgasm":
            self.output_vocab_to_chat("#CumForMe", callback=self._finish_orgasm)
        else:
            self.output_vocab_to_chat("#StopStroking", callback=self._finish_chatting)

    def _finish_ruin(self):
        self.interpreter.orgasm_ruined = True
        self.interpreter._state = "chatting"
        self.stop()

    def _finish_orgasm(self):
        self.interpreter.orgasm_allowed = True
        self.interpreter._state = "chatting"
        self.stop()

    def _finish_chatting(self):
        self.interpreter._state = "chatting"
        self.stop()
