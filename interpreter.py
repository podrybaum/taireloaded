import os
import random

from PySide6.QtCore import QTimer
from datetime import datetime

from bus import Bus
from settings import Settings
from tai_exceptions import RuntimeErr
from utils import random_script
from tokenizer import Tokenizer
from parser import Parser
from dispatch import Dispatch
from dispatch_dict import DISPATCH_DICT
from tokens import HeadlineToken
from message_classes import SystemMessage, EmoteMessage, DommeMessage, UserMessage

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


class ExecutionFrame:
    def __init__(self, blocks, context):
        self.blocks = blocks
        self.pointer = 0
        self.headlines = []
        self.context = context
        self.handler = None
        for i, block in enumerate(self.blocks):
            if isinstance(block, HeadlineToken):
                self.headlines.append(block.value, i + 1)


class Interpreter:
    def __init__(self):
        self._show_wait = False
        self.settings = Settings()
        self._output_buffer = ""
        self._null_domme_image = False
        self._bookmark_link = None  # If this holds a value, a module should call the specified link file and return to the appropriate place in the file instead of calling a new link
        self._bookmark_module = None  # As above, but for modules, and triggered when a link file hits @End
        self._emote_message = False  # If true, output an EmoteMessage instead of a DommeMessage
        self._system_message = False  # If true, output a SystemMessage instead of a DommeMessage
        self._stroke_time = 0
        self._tease_time = random.randint(self.settings.min_tease_length, self.settings.max_tease_length)
        self._tease_timer = QTimer()
        self._tease_timer.setSingleShot(True)
        self._tease_timer.timeout.connect(lambda: setattr(self, "_finish_tease", True))
        self._tease_timer.start(self._tease_time * 1000)
        self._stack = []
        self._media_locked = False
        self._current_frame = None
        self._hide_chat = False
        self._present = []
        self._temp_flags = []
        self._present = []  # list of entities currently in the chat, "D" is the domme, 1-6 for contacts 1-6
        self._state = "chatting"  # one of [stopped, chatting, stroking, chastity_stroking, edging, holding, long_hold, extreme_hold, cbt_balls, cbt_cock, cbt, waiting_for_input]
        self._hide_chat = False  # implements @HideChatMessage
        self._finish_tease = False  # if true, the tease timer has expired and the next module file needs to call an "end" script when reaching an @End
        self._interrupts_enabled = True
        self._subname_temp = None
        self._petname_temp = None
        self._dont_advance = False
        self._worship_mode = False
        self._worship_mode_target = None
        self._paused = False

        # Session Outcome Flags

        self.rapid_text = False
        self.responses = {}
        self.register_events()

        # these attributes are exposed to the scripting environment
        self.orgasm_allowed = False
        # we *could* override setattr on this class to implement updating the last_orgasm_date/last_ruin_date
        # values in settings whenever one of these two attributes is changed, and then we could deprecate the
        # @UpdateOrgasm and @UpdateRuin commands
        self.orgasm_ruined = False
        self.orgasm_denied = False
        self.orgasm_restricted = False
        self.AFK = False
        self.in_chastity = False
        self.last_joined = ""  # implements #LastJoined
        self.tna_result = None
        self.round = 0
        self.edges = 0
        self.cbt_balls = 0
        self.domme_mood = 5  # TODO: Should this persist across sessions perhaps?
        self.active_domme = self.settings.Domme.name

    def register_events(self):
        Bus.register("start", self._on_start)
        Bus.register("end_tease", lambda *args: setattr(self, "_state", "stopped"))
        Bus.register("set_AFK", self._on_set_AFK)
        Bus.register("add_entity", self._on_add_entity)
        Bus.register("remove_entity", self._on_remove_entity)
        Bus.register(
            "add_edge_hold_time", lambda x: setattr(self, "_edge_hold_time", getattr(self, "_edge_hold_time", 0) + x)
        )
        Bus.register("add_stroke_time", lambda x: setattr(self, "_stroke_time", self._stroke_time + x))
        Bus.register("add_tease_time", lambda x: self._tease_timer.start(self._tease_timer.remainingTime() + x * 1000))
        Bus.register("get_settings", lambda x: setattr(x, "settings", self.settings))
        Bus.register("get_runtime", lambda x: setattr(x, "runtime", self))
        Bus.register("bookmark_link", self._on_bookmark_link)
        Bus.register("bookmark_module", self._on_bookmark_module)
        Bus.register("runtime_goto", self.goto)
        Bus.register("runtime_mode", lambda x: setattr(self, "_mode", x))
        Bus.register("lock_media", lambda x: setattr(self, "_media_locked", x))
        Bus.register("interpreter_ready", self.run)
        Bus.register("pause_session", self._on_pause_session)
        Bus.register("resume_session", self._on_resume_session)

        # Hooks for state transitions and loops
        Bus.register("start_stroking", self._on_start_stroking)
        Bus.register("stop_stroking", self._on_stop_stroking)
        Bus.register("edge_start", self._on_edge_start)
        Bus.register("edge_stop", self._on_edge_stop)
        Bus.register("start_hold", self._on_start_hold)
        Bus.register("stop_hold", self._on_stop_hold)
        Bus.register("new_message", self._on_new_message)

    def _on_pause_session(self):
        self._paused = True

    def _on_resume_session(self):
        if self._paused:
            self._paused = False
            if self._state not in ("stopped", "waiting_for_input"):
                Bus.emit("interpreter_ready")

    def _on_bookmark_link(self):
        self._bookmark_link = (self._current_frame, self._current_frame.pointer + 2)

    def _on_bookmark_module(self):
        self._bookmark_module = (self._current_frame, self._current_frame.pointer + 2)

    def _on_add_entity(self, entity):
        if entity in self._present:
            return
        self._present.append(entity)
        if entity == "D":
            self.last_joined = self.settings.Domme.name
        else:
            self.last_joined = self.settings.contact_namespace(entity, "name")
        if not getattr(self, "_hide_chat", False):
            from message_classes import SystemMessage

            Bus.emit("new_message", SystemMessage(f"{self.last_joined} has joined the chat."))
        else:
            self._hide_chat = False
        Bus.emit("refresh_avatars", self._present.copy())

    def _on_remove_entity(self, entity):
        if entity not in self._present:
            return
        self._present.remove(entity)
        if entity == "D":
            name = self.settings.Domme.name
        else:
            name = self.settings.contact_namespace(entity, "name")
        if not getattr(self, "_hide_chat", False):
            from message_classes import SystemMessage

            Bus.emit("new_message", SystemMessage(f"{name} has logged out."))
        Bus.emit("refresh_avatars", self._present.copy())

    def _on_set_AFK(self, arg):
        if arg != self.AFK:
            self.AFK = not self.AFK
            if self.AFK:
                Bus.emit("new_message", SystemMessage(f"{self.settings.active_domme} has gone AFK."))
            else:
                Bus.emit("new_message", SystemMessage(f"{self.settings.active_domme} has returned."))

    def _on_start_stroking(self):
        self._state = "stroking"
        self._stroke_timer = QTimer()
        self._stroke_timer.setSingleShot(True)
        self._stroke_time = random.randint(self.settings.taunt_cycle_min, self.settings.taunt_cycle_max)
        self._stroke_timer.timeout.connect(lambda: Bus.emit("stop_stroking"))
        self._stroke_timer.start(self._stroke_time * 1000)

    def _on_stop_stroking(self):
        timer_was_active = False
        if hasattr(self, "_stroke_timer") and self._stroke_timer is not None:
            timer_was_active = self._stroke_timer.isActive()
            self._stroke_timer.stop()
            self._stroke_timer = None

        if self._state not in ["stroking", "chastity_stroking"]:
            return

        self._state = "chatting"

        if not timer_was_active:
            # The timer was already inactive, meaning it expired naturally rather than
            # being interrupted by a script command. Output the vocab response!
            vocab_line = Dispatch.vocab("#StopStroking")
            Bus.emit("new_message", DommeMessage(self.active_domme, vocab_line))

    def _on_edge_start(self):
        self._state = "edging"
        self.settings._edge_start = datetime.now()

    def _on_edge_stop(self):
        if self._state == "edging":
            self._state = "chatting"
            Bus.emit("metro_stop")
            delta = (datetime.now() - self.settings._edge_start).total_seconds()
            self.settings.Sub._cumulative_edge_time += delta
            self.settings.Sub._edges_all_time += 1
            self.settings.Sub.avg_edge_time = (
                self.settings.Sub._cumulative_edge_time / self.settings.Sub._edges_all_time
            )

    def _on_start_hold(self, length):
        if length == "extreme":
            self._state = "extreme_hold"
            time_val = (
                random.randint(self.settings.Sub.min_extreme_hold_time, self.settings.Sub.max_extreme_hold_time) * 60
            )
        elif length == "long":
            self._state = "long_hold"
            time_val = random.randint(self.settings.Sub.min_long_hold_time, self.settings.Sub.max_long_hold_time)
        else:
            self._state = "holding"
            time_val = random.randint(self.settings.Sub.min_edge_hold_time, self.settings.Sub.max_edge_hold_time)

        self._hold_timer = QTimer()
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(lambda: Bus.emit("stop_hold"))
        self._hold_timer.start(time_val * 1000)

    def _on_stop_hold(self):
        if self._state in ["holding", "long_hold", "extreme_hold"]:
            Dispatch.vocab("#StopStrokingHold")  # TODO: Add this vocab file
            self._state = "chatting"

    def _on_new_message(self, message):
        if isinstance(message, UserMessage):
            msg_text = message.text.lower()
            # Check if user indicates edge resolving
            if self._state == "edging" and any(word in msg_text for word in ["edge", "edging"]):
                Bus.emit("edge_stop")
                return

            for trigger, file_path in self.responses.items():
                if trigger in msg_text:
                    if self._execute_response_script(file_path):
                        return
                    break

        elif isinstance(message, DommeMessage):
            if not self._dont_advance:
                if getattr(self, "_worship_mode", False):
                    if self._worship_mode_target:
                        Bus.emit("show_image_tag_any", [self._worship_mode_target.lower()])
                    else:
                        Bus.emit("next_slide")
                else:
                    Bus.emit("next_slide")
            else:
                self._dont_advance = False

    def _load_response_files(self):
        responses_path = os.path.join(
            APPLICATION_ROOT, "Scripts", self.settings.current_personality, "Vocabulary", "Responses"
        )
        if not os.path.exists(responses_path):
            return

        for root, _, files in os.walk(responses_path):
            for file in files:
                if not file.endswith(".txt"):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if not lines:
                            continue

                        trigger_line = lines[0].strip()
                        if not trigger_line:
                            continue

                        phrases = [p.strip().lower() for p in trigger_line.split(",")]
                        for phrase in phrases:
                            if not phrase:
                                continue
                            if phrase in self.responses:
                                RuntimeErr(
                                    f"Response file trigger conflict: '{phrase}' exists in {self.responses[phrase]} AND {file_path}"
                                ).throw()
                            self.responses[phrase] = file_path
                except Exception:
                    pass

    def _execute_response_script(self, file_path):
        target_section = None
        if self._current_frame and self._current_frame.context == "start":
            target_section = "Before Tease"
        elif self.round == 1 and self._state == "chatting":
            target_section = "First Round"
        elif self._state == "stroking":
            target_section = "Stroking"
        elif self.round != 1 and self._state != "stroking" and self._state != "edging":
            target_section = "Not Stroking"
        elif self._state == "edging":
            target_section = "Edging"
        elif self._state in ["holding", "long_hold", "extreme_hold"]:
            target_section = "Holding The Edge"
        elif self._state == "cbt_cock":
            target_section = "CBT Cock"
        elif self._state == "cbt_balls":
            target_section = "CBT Balls"
        elif self.in_chastity:
            # TODO: Research legacy chastity response handling
            target_section = "Chastity"
        elif self._current_frame and self._current_frame.context == "end":
            target_section = "After Tease"

        if not target_section:
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start_idx = -1
        end_idx = -1

        for i, line in enumerate(lines):
            line_str = line.strip()
            if line_str == f"[{target_section}]":
                start_idx = i + 1
            elif start_idx != -1 and line_str == f"[{target_section} End]":
                end_idx = i
                break

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            extracted_text = "".join(lines[start_idx:end_idx])
            tokenizer = Tokenizer(extracted_text, file_path, line=start_idx + 1)
            tokenizer.run()
            parser = Parser(tokenizer.tokens)
            parser.run()

            frame = ExecutionFrame(parser.blocks, "response")
            self._stack.append(frame)
            self._current_frame = self._stack[-1]
            self.run()
            return True

        return False

    def execute_memory_script(self, text, source_name="memory", context="snippet"):
        tokenizer = Tokenizer(text, source_name, line=1)
        tokenizer.run()
        parser = Parser(tokenizer.tokens)
        parser.run()
        frame = ExecutionFrame(parser.blocks, context)
        self._stack.append(frame)
        self._current_frame = self._stack[-1]
        self.run()

    def _on_start(self):
        if self.settings.current_personality is None:
            return RuntimeErr("You must select a personality before starting a session!").throw()
        self._load_response_files()
        self._tease_timer.start()
        self.call(
            random_script(os.path.join(APPLICATION_ROOT, "Scripts", self.settings.current_personality, "Stroke\\Start"))
        )

    def block(self):
        try:
            return self._current_frame.blocks[self._current_frame.pointer]
        except Exception:
            return False

    def call(self, script, goto=None):
        if not os.path.isfile(script):
            return RuntimeErr(f"Script file not found: {script}").throw()
        self._stack = [self.parse_script(script)]
        self._current_frame = self._stack[-1]
        if goto is not None:
            self.goto(goto)
        self.run()

    def call_return(self, script, goto=None):
        if not os.path.isfile(script):
            return RuntimeErr(f"Script file not found: {script}").throw()
        self._stack.append(self.parse_script(script))
        self._current_frame = self._stack[-1]
        if goto is not None:
            self.goto(goto)
        self.run()

    def generic_visit(self, other):
        self._position = other.get_position()
        return other.Accept(self)

    def get_position(self):
        return self._position

    def VisitStringToken(self, other):
        self._output_buffer += other.value

    def VisitFunctionCall(self, other):
        func = getattr(Dispatch, DISPATCH_DICT[other.value]["implemented_by"])
        return func(self, *other.params)

    def VisitKeywordToken(self, other):
        func = getattr(Dispatch, DISPATCH_DICT[other.value]["implemented_by"])
        result = func(self, *other.params)
        if result is not None:
            self._output_buffer += str(result)
        else:
            # This is a developer fuckup, so we raise, not throw.
            raise RuntimeError(f"Critical: Encountered #Keyword token that doesn't return a value! {other.value}")

    def VisitVarRef(self, other):
        value = other.Evaluate()
        if value is not None and str(value).startswith("MISSING_VARIABLE_FILE"):
            RuntimeErr(f"Variable file for {other.filename} could not be read.", *other.get_position()).throw()
        elif value is not None:
            self._output_buffer += str(value)

    def VisitCommandFilter(self, other):
        RuntimeErr(f"Command filter ({other.value}) was called in an invalid context.", *other.get_position()).throw()

    def VisitFilterLine(self, other):
        for expr in other.filters:
            if hasattr(expr, "Evaluate"):
                if not expr.Evaluate():
                    return
            else:
                if not expr.Accept(self):
                    return
        for stmt in other.stmts:
            if getattr(self, "_abort_line", False):
                self._abort_line = False
                return
            self.generic_visit(stmt)

    def VisitMultipleChoiceBlock(self, other):
        self._state = "waiting_for_input"
        Bus.emit("show_input_cue")

        def handle_block(input, *args):
            if isinstance(input, UserMessage):
                for responseline in other.responselines:
                    for response in responseline.responses:
                        if response in input.txt:
                            self.generic_visit(responseline.stmts)
                            Bus.unsub("new_message", handle_block)
                            Bus.emit("hide_input_cue")
                            self._state = "chatting"
                            return

                if other.block_end.block_end.value == "@AcceptAnswer":
                    self.generic_visit(other.block_end.stmts)
                    Bus.unsub("new_message", handle_block)
                    Bus.emit("hide_input_cue")
                    self._state = "chatting"
                    return
                elif other.block_end.block_end.value == "@DifferentAnswer":
                    self.generic_visit(other.block_end.stmts)
                    return

        Bus.sub("new_message", handle_block)
        self.generic_visit(other.question)

    def goto(self, goto_headline):
        for headline_tuple in self._current_frame.headlines:
            headline, pointer = headline_tuple
            if headline == goto_headline:
                self._current_frame.pointer = pointer

    def parse_script(self, script):
        with open(script, "r") as f:
            tokenizer = Tokenizer(f.read(), script)
            tokenizer.run()
            parser = Parser(tokenizer.tokens)
            context = None
            personality_path = os.path.join(APPLICATION_ROOT, "Scripts", self.settings.current_personality)
            if os.path.dirname(script) == os.path.join(personality_path, "Stroke\\Link"):
                context = "link"
            elif os.path.dirname(script) == os.path.join(personality_path, "Modules"):
                context = "module"
            elif os.path.dirname(script) == os.path.join(personality_path, "Stroke\\Start"):
                context = "start"
            elif os.path.dirname(script) == os.path.join(personality_path, "Stroke\\End"):
                context = "end"
            else:
                context = "custom"
            return ExecutionFrame(parser.blocks, context)

    def run(self):
        if self._paused:
            return
        if self._state == "stopped" or self._state == "waiting_for_input":
            return

        # Taunt cycles drive their own execution via QTimer — run() is a no-op while one is active.
        if self._current_frame is None or self._current_frame.context == "taunt":
            return

        if block := self.block():
            self.generic_visit(block)

        waiting_for_chat = False
        if self._output_buffer != "":
            if self._system_message:
                Bus.emit("new_message", SystemMessage(self._output_buffer))
            elif self._emote_message:
                Bus.emit("new_message", EmoteMessage(self.active_domme, self._output_buffer))
                waiting_for_chat = True
            else:
                Bus.emit("new_message", DommeMessage(self.active_domme, self._output_buffer))
                waiting_for_chat = True

            self._output_buffer = ""
            self._system_message = False
            self._emote_message = False
        else:
            if self._null_domme_image and not self._media_locked:
                Bus.emit("next_slide")
                self._null_domme_image = False

        self._current_frame.pointer += 1
        if self._current_frame.pointer >= len(self._current_frame.blocks):
            if self._current_frame.context == "response":
                self._stack.pop()
                self._current_frame = self._stack[-1]
            else:
                RuntimeErr("End of file reached without encountering @End", *self.get_position()).throw()

        if not waiting_for_chat:
            Bus.emit("interpreter_ready")
