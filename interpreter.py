from contextlib import contextmanager

from bus import Bus
from datetime import datetime
import random
from kivymd.app import Clock
from message_classes import UserMessage, SystemMessage, EmoteMessage, DommeMessage
from tokenizer import Tokenizer
from tokens import OperatorToken, StringToken, HeadlineToken
from ast_classes import BinaryExpression
from parser import Parser
import os
from dispatch import Dispatch
from dispatch_dict import DISPATCH_DICT
from tai_exceptions import RuntimeErr

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


# TODO: Build censor bars and image bars
# TODO: Build @Edge logic - Implement @InterruptLongEdge - Decide how to handle @MultipleEdges
# TODO: Implement @SendDailyTask
# TODO: Add something to the UI for @ShowWait and Question mode
# TODO: Implement TnAFastSlides, etc
# TODO: Implement "Worship Mode"
# TODO: Implement 'standard' flow: Start > Link > Module > Link > Module > End
# TODO: Add domme/contact avatar overlays on "video screen"
# TODO: Implement responses
# TODO: Handle setting runtime context for @Call family
# TODO: Handle incrementing timer for tease_time


# self.blocks represents the "stack" of AST objects returned by parsing a script.
# to support @CallReturn and similar commands properly, we need to be careful about how we handle it.
# whenever we add a new script to the stack, we always do self.blocks = blocks.extend(self.blocks) so
# that the newly added ast objects are on "top" of the stack.   when we hit an @End, we record its
# path attribute and iterate over self.blocks, popping blocks while the .path attribute matches
# if we hit @CallReturn, we discard the rest of the current block but leave the rest of the current script
# on the stack, placing the newly parsed blocks on top.  If we hit @Call, we dump the entire stack and replace it
# with the called script. We don't pop blocks from the stack in order to execute them
# we maintain a pointer to a position on the stack and traverse by moving the pointer.   When we hit @Goto
# we record the path attribute from its get_position() method and iterate through the stack while stack[pointer].get_position()[2] == path,
# looking for a matching HeadlineToken.  If the lookahead's path attribute doesn't match and we haven't found a headline yet, we move the pointer
# back to the top of the stack and resume searching.  (this implements 'backwards goto').
# this should maintain the "CallReturn stack" correctly, handle 'backwards goto' and correctly trim the stack when we exit from a completed
# script.
class Interpreter:
    def __init__(self, settings):
        self.blocks = []
        self.pointer = 0
        self.settings = settings
        personality_path = os.path.join(APPLICATION_ROOT, "Scripts", self.settings.current_personality)
        self.flag_path = os.path.join(personality_path, "\\System\\Flags\\")
        self.var_path = os.path.join(personality_path, "\\System\\Variables\\")
        self.game_path = os.path.join(personality_path, "Game Modules")
        self.vocab_path = os.path.join(personality_path, "Vocabulary")
        self.stroke_path = os.path.join(personality_path, "Stroke")
        self.custom_path = os.path.join(personality_path, "Custom")
        self._taunt_clock = None
        self._bookmark_link = False
        self._bookmark_module = False
        self._context = "start"  # "start", "end", "link", "module", "interrupt", "question"
        self._taunt_context = ""  # "stroke", "extreme_hold", "long_hold", "normal_hold", "chastity_stroke"
        self._current_image_path = ""
        self._custom_mode = None
        self._custom_mode_triggers = None
        self._domme_avatar_backup = None
        self._domme_name_backup = None
        self._dont_advance = False
        self._edge_start = None
        self._emote_message = False
        self._hide_chat = False
        self._loop_answer = False
        self._null_domme_image = False
        self._position = (0, 0, "")
        self._present = set()
        self._present.add(0)
        self._previous_context = None
        self._rapid_text = False
        self._response_no = False
        self._response_yes = False
        self._response_script = ""
        self._show_wait = False
        self._slides_dir = ""
        self._slides = []
        self._stroke_start = None
        self._system_message = False
        self._temp_flags = set()
        self.active_domme = settings.Domme
        self.AFK = False  # <- state of AFK
        self.cbt_balls = 0
        self.domme_mood = 5  # <- current domme mood value
        self.domme_name_temp = None
        self.edge_hold_time = 0
        self.edges = 0
        self.edging_state = False
        self.holding_state = False
        self.in_chastity = False  # <- state of chastity
        self.interrupt_state = True
        self.last_joined = ""
        self.media_locked = False  # <- is media locked
        self.orgasm_allowed = False
        self.orgasm_denied = False
        self.orgasm_restricted = False
        self.orgasm_ruined = False
        self.petname_temp = ""  # <- As above
        self.rapid_text = False
        self.round = 0
        self.stroke_time = 0  # <- remaining stroke time (in seconds)
        self.stroking_state = False  # <- state of stroking
        self.subname_temp = None  # <- @SubNameTemp sets this
        self.tease_time = random.randint(self.settings.min_tease_length, self.settings.max_tease_length)
        self.tna_fast_slides_result = ""
        self.video_is_paused = False
        self.video_is_playing = False
        self.video_is_slow_motion = False
        self.video_length = 0
        self.video_remaining = 0
        self.worship_mode_target = None  # <- Worship mode target
        self.output_buffer = []
        Bus.register("edge_start", self._on_edge_start)
        Bus.sub("new_message", self._on_new_message)
        Bus.register("stop_stroking", self._on_stop_stroking)
        Bus.register("start_stroking", self._on_start_stroking)
        Bus.register("interpreter_ready", self.execute)
        Bus.register("start_hold", self._on_start_hold)
        Bus.register("stop_hold", self._on_stop_hold)
        Bus.register("rapid_text_setting_requested", self._on_rapid_text_request)
        Bus.sub("video_eos", self._on_video_eos)
        Bus.register("set_personality", self._on_set_personality)
        Bus.register("start", self._on_start)

    def _on_start(self, *args):
        if self.settings.current_personality is None:
            return RuntimeErr("You must select a personality before starting!").throw()
        folder = os.path.join(APPLICATION_ROOT, "Scripts", self.settings.current_personality, "Start")
        scripts = os.listdir(folder)
        self.execute_script(random.choice(scripts))

    def _on_set_personality(self, name, *args):
        self.settings.current_personality = name

    def domme_id_to_obj(self, id):
        if id == "D":
            return self.settings.Domme
        else:
            return self.settings.contact_namespace(id, "object")

    def goto(self, headline: HeadlineToken):
        Dispatch.Goto(self, headline)

    def _on_video_eos(self):
        if self.mode is not None and self.mode.mode == "video":
            del self.mode
            self.mode = None

    def _on_rapid_text_request(self, dict):
        dict["rt"] = self.rapid_text

    def _on_start_hold(self, length):
        if length == "normal":
            duration = random.randint(self.settings.Sub.min_hold_time, self.settings.Sub.max_hold_time)
            self._taunt_context = "normal_hold"
        if length == "long":
            duration = random.randint(self.settings.Sub.min_long_hold_time, self.settings.Sub.max_long_hold_time)
            self._taunt_context = "long_hold"
        if length == "extreme":
            duration = random.randint(self.settings.Sub.min_extreme_hold_time, self.settings.Sub.max_extreme_hold_time)
            self._taunt_context = "extreme_hold"
        self._taunt_clock = Clock.schedule_once(Bus.emit("stop_hold"), duration)
        self.run_taunts()

    def _on_stop_hold(self):
        # TODO: I'm fairly certain the only way this happens is if the clock expires.  I don't think any commands
        #       exist that interrupt a hold.
        #       Do we need to consider disabling interrupts automatically during this state?
        self._taunt_context = ""
        # TODO: chat output, state management, etc.

    @contextmanager
    def isolate_for_task(self):
        """Context manager that unsubscribes the interpreter from events that could trigger it to execute
        new input when we don't want it to."""
        Bus.unsub("new_message", self._on_new_message)
        Bus.unsub("interpreter_ready", self.execute)
        try:
            yield
        finally:
            Bus.sub("new_message", self._on_new_message)
            Bus.sub("interepreter_ready", self.execute)

    def execute_script(self, path):
        if os.path.isfile(path):
            with open(path, "r") as f:
                content = f.read()
        else:
            raise RuntimeError(f"Script file {path} not found.")
        tokenizer = Tokenizer(content, path)
        tokenizer.run()
        parser = Parser(tokenizer.tokens)
        parser.run()
        self.insert_blocks(parser.blocks)

    def execute_string(self, string, path, lineno):
        tokenizer = Tokenizer(string, path, lineno)
        tokenizer.run()
        parser = Parser(tokenizer.tokens)
        parser.run()
        if len(parser.blocks > 1):
            raise RuntimeError(f"More than one block returned from string execution. {path}: {lineno}")
        with self.isolate_for_task():
            self.generic_visit(parser.blocks[0])

    def get_position(self):
        return self._position

    def insert_blocks(self, blocks):
        self.blocks = blocks.extend(self.blocks)

    def empty_buffer(self):
        string = "".join(self.output_buffer)
        if len(string) == 0 or all(string == " ") or all(string == ""):
            return True
        return False

    def VisitCommandFilter(self, other):
        func = getattr(Dispatch, DISPATCH_DICT[other.value]["implemented_by"])
        return func(self, *other.params)

    def VisitMultipleChoiceBlock(self, other):
        # TODO: UI indicator for question mode
        Bus.unsub("interpreter_ready", self.execute)
        Bus.unsub("new_message", self._on_new_message)

        def handle_block(input, *args):
            if isinstance(input, UserMessage):
                for responseline in other.responselines:
                    if input.txt in responseline.responses:
                        # Handle @LoopAnswer
                        self.generic_visit(responseline.stmts)
                        if self._loop_answer:
                            return
                        Bus.unsub("new_message", handle_block)
                        Bus.sub("new_message", self._on_new_message)
                        Bus.sub("interpreter_ready", self.execute)
                        return
                if other.block_end.block_end.value == "@DifferentAnswer":
                    self.generic_visit(other.block_end.stmts)
                    return  # don't change subs, just handle the chat output and wait for a new response
                elif other.block_end.block_end.value == "@AcceptAnswer":
                    Bus.unsub("new_message", handle_block)
                    Bus.sub("new_message", self._on_new_message)
                    Bus.sub("interpreter_ready", self.execute)
                    return self.generic_visit(other.block_end.stmts)

        Bus.sub("new_chat_message", handle_block)
        self.generic_visit(other.question)

    def VisitVarRef(self, other):
        pass  # TODO we need to work out what context we're in and figure out what to do with variable
        # It may be the case that we'll only see VarRef inside a binary expression, in which case, we'll
        # know what to do... if we're visiting a VarRef, it's probalby holding string data that's just chat ouput
        # So our default handling here is probably just to look up and return the value

    def VisitFilterLine(self, other):
        list()
        # The filters list is a list of operands and operators in Reverse Polish Notation
        # if other.filters[0] is an operand, put it on the stack, if it's an operator, pop the
        # top 2 items from the stack, do the operation and put the result back on the stack
        # (rather than do the operation in this step, we create the binary expressions)
        stack = []
        while len(other.filters) > 0:
            if isinstance(tok := other.filters.pop(0), OperatorToken):
                b = stack.pop()
                a = stack.pop()
                stack.append(BinaryExpression(a, tok, b))
            else:
                stack.append(tok)
        # Now evaluate expression objects on the stack, if any are False, we skip the current line
        for expr in stack:
            if hasattr(expr, "Evaluate"):
                if not expr.Evaluate():
                    return
            else:
                if not expr.Accept(self):
                    return
        for stmt in other.stmts:
            self.generic_visit(stmt)

    def generic_visit(self, other):
        self._position = other.get_position()
        return other.Accept(self)

    def execute(self):
        self.generic_visit(self.blocks[self.pointer])
        if not self.empty_buffer:
            if self._response_no or self._response_yes:
                # We're about to output the next chat message, so it makes sense to cancel these now
                # we've given the user as much chance to respond as we can without getting into a state
                # that doesn't make sense.
                self._response_no = False
                self._response_yes = False
                self._response_script = ""
            if self.system_message:
                Bus.emit("new_message", SystemMessage("".join(self.output_buffer)))
                self.system_message = False
            elif self.emote_message:
                if not self.media_locked:
                    Bus.emit("next_slide")
                Bus.emit("new_message", EmoteMessage("".join(self.output_buffer)))
                self.emote_message = False
            else:
                if not self.media_locked:
                    Bus.emit("next_slide")
                Bus.emit("new_message", DommeMessage(self.active_domme, "".join(self.output_buffer)))
            self.output_buffer = []
            self.pointer += 1
            return  # we just return here.  after the chat output has been handled, the ui will call interpreter_ready
        else:
            if self._null_domme_image and not self.media_locked:
                Bus.emit("next_slide")
            self.pointer += 1
            Bus.emit("interpreter_ready")
            # no chat delay or other async events to wait for, so we notify ourselves to advance

    def run_taunts(self):
        # TODO: figure out what kind of taunts we need to run (check self._taunt_context)
        #       parse the appropriate script into a temporary stack (self._taunt_stack)
        #       schedule the next step using the clock.  clock needs to be canceled if we respond to another event
        #       select a block at random from the stack, evaluate filters if any.  if filters evaluate False, pick again.
        #       execute the line, goto step 3.
        if self._taunt_context == "stroke":
            pass
        elif self._taunt_context == "edge":
            pass
        elif self._taunt_context == "normal_hold":
            pass
        elif self._taunt_context == "long_hold":
            pass
        elif self._taunt_context == "extreme_hold":
            pass
        elif self._taunt_context == "chastity_stroke":
            pass

    def _on_start_stroking(self):
        self.stroking_state = True if not self.in_chastity else False
        self._taunt_context = "stroke" if not self.in_chastity else "chastity_stroke"
        self.stroke_time = random.randint(self.settings.taunt_cycle_min, self.settings.taunt_cycle_max)
        self.taunt_clock = Clock.schedule_once(Bus.emit("stop_stroking"), self.stroke_time)
        self.run_taunts()

    def _on_stop_stroking(self):
        """triggered when it's time for the sub to stop stroking"""
        # TODO: think we need to know for sure where this event came from.  if from a taunt_clock, we need
        #       to handle #StopStroking ourselves, I think.  If not from a taunt_clock and we have a taunt_clock
        #       running we need to cancel it (not sure if this happens, maybe through @Interrupt somehow?)
        self.stroking_state = False
        self._taunt_context = ""

    def _on_edge_start(self):
        self.edging_state = True
        self._edge_start = datetime.now()
        self._taunt_context = "edge"
        self.run_taunts()

    def _on_edge_stop(self):
        self.edges += 1
        self.settings.Sub._edges_all_time += 1
        delta = datetime.now() - self._edge_start
        self.settings.Sub._cumulative_edge_time += delta.total_seconds()
        self.settings.Sub.avg_edge_time = round(
            self.settings.Sub._cumulative_edge_time / self.settings.Sub._edges_all_time
        )
        self._taunt_context = ""
        # TODO: produce chat output, change state, etc.

    def _on_new_message(self, message):
        # TODO: It's not always going to be correct for chat output to advance the script.  It's context-dependant
        #       So we don't emit interpreter_ready when self._taunt_context is populated.  We need to work out
        #       if that's the only relevant condition.
        if isinstance(message, UserMessage):
            if self.edging_state:
                for word in ["edge", "edging"]:
                    if word in message.text:
                        Bus.emit("edge_stop")
                        break
            if self._response_no:
                if self.compare_input_to_vocab(message.text, os.path.join(self.vocab_path, "#No.txt")):
                    Dispatch.Goto(StringToken(*self.get_position(), self._response_script))
                    self._response_no = False
                    self._response_script = ""
            elif self.resposne_yes:
                if self.compare_input_to_vocab(message.text, os.path.join(self.vocab_path, "#Yes.txt")):
                    Dispatch.Goto(StringToken(*self.get_position(), self._response_script))
                    self._response_yes = False
                    self._response_script = ""
        if isinstance(message, EmoteMessage):
            self._emote_message = False
        if isinstance(message, SystemMessage):
            self._system_message = False
        if self._taunt_context == "":
            Bus.emit("interpreter_ready")

        # TODO: handle safeword?   does anyone seriously use that shit?

    def compare_input_to_vocab(self, input, vocab):
        file = os.path.join(self.vocab_path, vocab)
        with open(file, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line in input:
                    return True
        return False
