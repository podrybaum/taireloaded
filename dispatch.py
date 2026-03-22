import os
import random
import shutil
from datetime import datetime, timedelta

from bus import Bus
from dispatch_dict import DISPATCH_DICT
from message_classes import SystemMessage, UserMessage
from tokens import StringToken, IntegerToken, HeadlineToken
from tai_exceptions import SyntaxErr, TypeErr, ValueErr, RuntimeErr
from custom_mode import CustomMode
from utils import (
    convert_string_time_to_seconds,
    is_image_file,
    random_script,
    date_from_string,
    random_video,
    is_video_file,
    string_from_date,
    is_valid_filename,
)
from kivymd.app import Clock

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))

HANDLER_TO_CMD = {}
for cmd, info in DISPATCH_DICT.items():
    impl = info.get("implemented_by")
    if impl:
        HANDLER_TO_CMD[impl] = cmd

# used to coerce the parameter types in the dict to actual python types
TYPE_CHECK = {"string": str, "int": int, "bool": bool}


def validate_params(func):
    cmd_name = HANDLER_TO_CMD.get(func.__name__)

    # TODO:  add *string and *int cases
    def wrapper(*args):
        param_info = DISPATCH_DICT[cmd_name].get("parameters", [])
        max_params = len(param_info)
        required = sum(1 for p in param_info if not p.get("optional", False))

        if len(args) == 0 and required != 0:
            SyntaxErr(
                f"{cmd_name} requires {'at least' if required < max_params else 'exactly'} {required} parameters, got 0",
                0,
                0,
                "Position/path data not available.",
            ).throw()
            return

        if len(args) > 0 and max_params == 0:
            SyntaxErr(
                f"{cmd_name} expects no parameters, got {len(args)}", args[0].line, args[0].pos, args[0].path
            ).throw()
            return

        if len(args) > max_params:
            SyntaxErr(
                f"{cmd_name} expects at most {max_params} parameters, got {len(args)}",
                args[0].line,
                args[0].pos,
                args[0].path,
            ).throw()
            return
        elif len(args) < required:
            SyntaxErr(
                f"{cmd_name} requires {'at least' if required < max_params else 'exactly'} {required} parameters, got {len(args)}",
                args[0].line,
                args[0].pos,
                args[0].path,
            ).throw()
            return

        for i, token in enumerate(args):
            expected_str = param_info[i].get("type")
            expected_type = TYPE_CHECK.get(expected_str)

            if not isinstance(token, expected_type):
                TypeErr(
                    f"Parameter {i + 1} to {cmd_name} must be of type {expected_str}", token.line, token.pos, token.path
                ).throw()
                return

        return func(*args)

    return wrapper


# This metaclass allows us to 'register' methods at class creation so we can
# call them without worrying about what order we define them in.  Makes it possible
# to keep all the command implementation methods in alphabetical order, for ease of
# future maintenance.
class DispatchMeta(type):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls._registry = {}
        for _, value in dct.items():
            if callable(value) and hasattr(value, "_command_name"):
                cls._registry[value._command_name] = value


class Dispatch(metaclass=DispatchMeta):
    def register(name):
        def decorator(func):
            func._command_name = name
            return func

        return decorator

    @staticmethod
    def vocab(vocab_word):
        # NOTE: we enforce that system provided vocab files must only return
        #      a single string primitive per line, so unlike resolving a VocabToken
        #      we don't have to worry about tokenizing and parsing the return
        filename = f"{vocab_word}.txt"
        filepath = os.path.join(APPLICATION_ROOT, "\\Vocabulary\\", filename)
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                lines = f.readlines()
        index = random.randint(0, len(lines))
        return lines[index]

    @staticmethod
    def NOP(runtime, *args):
        pass
        # Done

    @validate_params
    @staticmethod
    def AFK(runtime, arg):
        runtime.AFK = arg.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def AcceptAnswer(runtime):
        pass  # doesn't need an implementation, we just match the string value
        # Done

    @validate_params
    @staticmethod
    def AddContact(runtime, arg):
        if arg.Evaluate() not in [1, 2, 3, 4, 5, 6]:
            ValueErr("Invalid contact number", *arg.get_position()).throw()
        runtime._present.add(arg.Evaluate())
        runtime.last_joined = runtime.settings.id_to_name(arg.Evaluate())
        if not runtime.hide_chat:
            Bus.emit("new_message", SystemMessage(f"{runtime.last_joined} has joined the chat."))
        else:
            runtime._hide_chat = False
        # Done

    @validate_params
    @staticmethod
    def AddDomme(runtime):
        runtime._present.add("D")
        runtime.last_joined = runtime.settings.Domme.name
        if not runtime.hide_chat:
            Bus.emit("new_message", SystemMessage(f"{runtime.last_joined} has joined the chat."))
        else:
            runtime.hide_chat = False
        # Done

    @validate_params
    @staticmethod
    def AddEdgeHoldTime(runtime, arg1=None, arg2=None):
        if arg1 is None:
            runtime.edge_hold_time += random.randomint(
                runtime.settings.Sub.min_edge_hold_time, runtime.settings.Sub.max_edge_hold_time
            )
        seconds = convert_string_time_to_seconds(arg1.Evaluate())
        if seconds == "invalid units":
            SyntaxErr("Invalid time units", *arg1.get_position()).throw()
        if arg2 is not None:
            arg2seconds = convert_string_time_to_seconds(arg2.Evaluate())
            if arg2seconds == "invalid units":
                SyntaxErr("Invalid time units", *arg2.get_position()).throw()
            runtime.edge_hold_time += random.randint(seconds, arg2seconds)
        else:
            runtime.edge_hold_time += arg1.Evaluate()
            # done

    @validate_params
    @staticmethod
    def AddStrokeTime(runtime, arg1=None, arg2=None):
        if arg1 is None:
            runtime.stroke_time += random.randomint(runtime.settings.TauntCycleMin, runtime.settings.TauntCycleMax)
        seconds = convert_string_time_to_seconds(arg1.Evaluate())
        if seconds == "invalid units":
            SyntaxErr("Invalid time units", *arg1.get_position()).throw()
        if arg2 is not None:
            arg2seconds = convert_string_time_to_seconds(arg2.Evaluate())
            if arg2seconds == "invalid units":
                SyntaxErr("Invalid time units", *arg2.get_position()).throw()
            runtime.stroke_time += random.randint(seconds, arg2seconds)
        else:
            runtime.stroke_time += arg1.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def AddTeaseTime(runtime, arg1=None, arg2=None):
        if arg1 is None:
            runtime.tease_time += random.randomint(runtime.settings.MinTeaseLength, runtime.settings.MaxTeaseLength)
        seconds = convert_string_time_to_seconds(arg1.Evalute())
        if seconds == "invalid units":
            SyntaxErr("Invalid time units", *arg1.get_position()).throw()
        if arg2 is not None:
            arg2seconds = convert_string_time_to_seconds(arg2.Evaluate())
            if arg2seconds == "invalid units":
                SyntaxErr("Invalid time units", *arg2.get_position()).throw()
            runtime.tease_time += random.randint(seconds, arg2seconds)
        else:
            runtime.tease_time += arg1.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def Afternoon(runtime):
        hour = datetime.now().hour
        return hour > 12 and hour < 19
        # Done

    @validate_params
    @staticmethod
    def AllowsOrgasm(runtime):
        return runtime.settings.Domme.allows_orgasms != 5
        # Done

    @validate_params
    @staticmethod
    def ApathyLevel(runtime, arg0):
        return runtime.settings.Domme.apathy_level == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def BeforeTease(runtime):
        return runtime.round < 1
        # Done

    @validate_params
    @staticmethod
    def BookmarkLink(runtime):
        if runtime._context == "link":
            runtime._bookmark_link = True
        # Done

    @validate_params
    @staticmethod
    def BookmarkModule(runtime):
        if runtime._context == "module":
            runtime._bookmark_module = True
        # Done

    @validate_params
    @staticmethod
    def Call(runtime, arg0, arg1=None):
        runtime.blocks = []
        runtime.execute_script(arg0.Evaluate())
        if arg1 is not None:
            Dispatch._registry["Goto"](arg1)
        # Done

    @validate_params
    @staticmethod
    def CallRandom(runtime, arg0):
        tok = StringToken(*arg0.get_position(), random_script(arg0.Evaluate()))
        Dispatch.Call(tok)
        # Done

    @validate_params
    @staticmethod
    def CallReturn(runtime, arg0, arg1=None):
        runtime.execute_script(arg0.Evaluate())
        if arg1 is not None:
            Dispatch._registry["Goto"](arg1)
        # Done

    @validate_params
    @staticmethod
    def CameMode(runtime, arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @CameMode must be one of 'video' or 'goto'." * arg0.get_position()
            ).throw()
        runtime.mode = CustomMode(arg0.Evaluate().lower(), arg1, ["came"])
        # Done

    @validate_params
    @staticmethod
    def CBT(runtime, arg0=None):
        path = os.path.join(APPLICATION_ROOT, "SystemScripts\\")
        if arg0 is None:
            first = random.choice([first for first in os.listdir(path) if first.endswith("_First.txt")])
        elif arg0.Evaluate().lower() == "cock":
            first = "CBTCock_First.txt"
        elif arg0.Evaluate().lower() == "balls":
            first = "CBTBalls_First.txt"
        else:
            ValueErr("Invalid parameter: argument to @CBT must be one of 'cock' or 'balls'", *arg0.get_position())
            if os.path.isfile(first):
                with open(first, "r") as f:
                    lines = f.readlines()
                index = random.randint(0, len(lines) - 1)
                line = lines[index]
                index += 1
                runtime.execute_string(line, first, index)
            else:
                RuntimeErr(f"Missing file for CBT task generation: {first}", *arg0.get_postion()).throw()
            files = [file for file in os.listdir(path) if file.startswith("CBT") and not file.endswith("_First.txt")]
            tasks = random.randint(1, 5) * runtime.settings.Sub.ctb_level
            if arg0 is None:
                file = random.choice(files)
            elif arg0.Evaluate().lower() == "cock":
                file = "CBTCock.txt"
            elif arg0.Evaluate().lower() == "balls":
                file = "CBTBalls.txt"

            if os.path.isfile(file):
                with open(file, "r") as f:
                    lines = f.readlines()
                while tasks > 0:
                    index = random.randint(0, len(lines) - 1)
                    line = lines[index]
                    index += 1
                    tasks -= 1
                    runtime.execute_string(line, first, index)
            else:
                RuntimeErr(f"Missing file for CBT task generation: {first}", *arg0.get_postion()).throw()
        # Done

    @validate_params
    @staticmethod
    def CBTLevel(runtime, arg0):
        return runtime.settings.Sub.CBTLevel == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def CensorbarOff(runtime, arg0, arg1):
        pass

    @validate_params
    @staticmethod
    def CensorbarOn(runtime, arg0, arg1, arg2, arg3, arg4, arg5):
        pass

    @validate_params
    @staticmethod
    def Chance(runtime, arg0, arg1):
        if random.randint(0, 100) < arg0.Evaluate():
            return Dispatch._registry["Goto"](arg1)
        # Done

    @validate_params
    @staticmethod
    def Chastity(runtime, arg0):
        runtime.in_chastity = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def ChastityPA(runtime):
        return runtime.settings.Sub.ChastityPiercing
        # Done

    @validate_params
    @staticmethod
    def ChastitySpikes(runtime):
        return runtime.settings.Sub.ChastitySpikes
        # Done

    @validate_params
    @staticmethod
    def ChatImage(runtime, arg0):
        return f'<img src="{arg0.Evaluate()}">'
        # Done

    @validate_params
    @staticmethod
    def CheckBnB(runtime):
        if not os.path.isdir(runtime.settings.boobs_images) or not os.path.isdir(runtime.settings.butts_images):
            tok = StringToken(*runtime.get_position(), "No BnB")
            return Dispatch._registry["Goto"](tok)
        else:
            files = os.path.listdir(runtime.settings.boobs_images)
            if len(files) == 0:
                tok = StringToken(*runtime.get_position(), "No BnB")
                return Dispatch._registry["Goto"](tok)
            files = os.path.listdir(runtime.settings.butts_images)
            if len(files) == 0:
                tok = StringToken(*runtime.get_position(), "No Bnb")
                return Dispatch._registry["Goto"](tok)
        # Done

    @validate_params
    @staticmethod
    def CheckDate(runtime, arg0, arg1=None, arg2=None):
        if os.path.isfile(os.path.join(runtime.var_path, arg0.Evaluate())):
            with open(os.path.join(runtime.var_path, arg0.Evaluate()), "r") as f:
                datestring = f.read()
            date = date_from_string(datestring)
            if arg1 is None and date < datetime.now():
                return True
            if arg1 and arg2 is None:
                delta_seconds = convert_string_time_to_seconds(arg1.Evaluate())
                if delta_seconds == "invalid units":
                    ValueErr("Invalid time units", *arg1.get_position()).throw()
                if date < datetime.now() - timedelta(seconds=delta_seconds):
                    return True
            if arg1 and arg2:
                delta_seconds = convert_string_time_to_seconds(arg1.Evaluate())
                if delta_seconds == "invalid units":
                    ValueErr("Invalid time units", *arg1.get_position()).throw()
                delta_seconds2 = convert_string_time_to_seconds(arg2.Evaluate())
                if delta_seconds2 == "invalid units":
                    ValueErr("Invalid time units", *arg2.get_position()).throw()
                if date < datetime.now() - timedelta(seconds=delta_seconds) and date > datetime.now() - timedelta(
                    seconds=delta_seconds2
                ):
                    return True
        else:
            return False
            # Done

    @validate_params
    @staticmethod
    def CheckFlag(runtime, arg0, arg1):
        path = os.path.join(runtime.flag_path, arg0.Evaluate())
        if os.path.isfile(path):
            Dispatch._registry["Goto"](arg1)
        # Done

    @validate_params
    @staticmethod
    def CheckJoiVideo(runtime):
        if not os.path.isdir(runtime.settings.joi_video):
            tok = StringToken(*runtime.get_position(), "No JOI Found")
            return Dispatch._registry["Goto"](tok)
        # Done

    @validate_params
    @staticmethod
    def CheckStrokingState(runtime):
        if runtime.stroking_state:
            tok = StringToken(*runtime.get_position(), "Sub Stroking")
            return Dispatch._registry["Goto"](tok)
        # Done

    @validate_params
    @staticmethod
    def CheckTnA(runtime):
        if runtime.tna_fast_slides_result == "Boobs":
            tok = StringToken(*runtime.get_position(), "Boobs")
            return Dispatch._registry["Goto"](tok)
        elif runtime.tna_fast_slides_result == "Butt":
            tok = StringToken(*runtime.get_position(), "Butt")
            return Dispatch._registry["Goto"](tok)
        # Done

    @validate_params
    @staticmethod
    def CheckVideo(runtime):
        video_dirs = [
            runtime.settings.joi_video,
            runtime.settings.hardcore_video,
            runtime.settings.softcore_video,
            runtime.settings.lesbian_video,
            runtime.settings.blowjob_video,
            runtime.settings.femdom_video,
            runtime.settings.femsub_video,
            runtime.settings.ch_video,
            runtime.settings.general_video,
        ]
        for video_dir in video_dirs:
            if not os.path.isdir(video_dir):
                tok = StringToken(*runtime.get_position(), "No Videos Found")
                return Dispatch._registry["Goto"](tok)
            files = os.listdir(video_dir)
            if len(files) == 0:
                tok = StringToken(*runtime.get_position(), "No Videos Found")
                return Dispatch._registry["Goto"](tok)
            tok = StringToken(*runtime.get_position(), "Videos Found")
            return Dispatch._registry["Goto"](tok)
        # Done

    @validate_params
    @staticmethod
    def ClearChat(runtime):
        Bus.emit("clear_chat")
        # Done

    @validate_params
    @staticmethod
    def ClearModes(runtime):
        if runtime.mode is not None:
            del runtime.mode
            runtime.mode = None
        # Done

    @validate_params
    @staticmethod
    def Contact(runtime, arg0):
        runtime.active_domme = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def ContactKeyword(runtime, arg0, arg1):
        return runtime.settings.contact_namespace(arg0.Evaluate(), arg1.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def ContinueVideo(runtime):
        Bus.emit("unpause_video")
        # Done

    @validate_params
    @staticmethod
    def CountVar(runtime, arg0):
        if not is_valid_filename(arg0.Evaluate()):
            ValueErr("Invalid filename specified for @CountVar", *arg0.get_position()).throw()

        def count():
            i = 0
            while True:
                with open(os.path.join(runtime.var_path, arg0.Evaluate()), "w") as f:
                    f.write(i)
                i += 1
                yield i

        Clock.schedule_interval(lambda _: next(count()), 1)
        # Done

    @validate_params
    @staticmethod
    def CumForMe(runtime):
        return Dispatch.vocab("#CumForMe")
        # Done

    @validate_params
    @staticmethod
    def CustomMode(runtime, arg0, arg1, arg2):
        mode = arg1.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @CustomMode must be one of 'video' or 'goto'",
                *arg1.get_position(),
            ).throw()
        runtime.mode = CustomMode(arg0.Evaluate(), mode, arg2)
        # Done

    @validate_params
    @staticmethod
    def CustomTask(runtime, arg0):
        filename = arg0.Evaluate()
        path = os.path.join(APPLICATION_ROOT, "Custon\\Tasks")
        first = os.path.join(path, filename + "_First.txt")
        if os.path.isfile(first):
            with open(first, "r") as f:
                lines = f.readlines()
            index = random.randint(0, len(lines) - 1)
            line = lines[index]
            index += 1
            runtime.execute_string(line, first, index)
        else:
            RuntimeErr(f"Missing file for custom task generation: {first}", *arg0.get_postion()).throw()
        file = os.path.join(path, filename + ".txt")
        tasks = random.randint(1, 5) * runtime.settings.Sub.ctb_level
        if os.path.isfile(file):
            with open(file, "r") as f:
                lines = f.readlines()
            while tasks > 0:
                index = random.randint(0, len(lines) - 1)
                line = lines[index]
                index += 1
                tasks -= 1
                runtime.execute_string(line, first, index)
        else:
            RuntimeErr(f"Missing file for custom task generation: {first}", *arg0.get_postion()).throw()
        # Done

    @validate_params
    @staticmethod
    def DateDifference(runtime, arg0, arg1):
        arg0 = date_from_string(arg0.Evaluate())
        if arg0 == "invalid units":
            ValueErr("Invalid date", *arg0.get_position()).throw()
        units = arg1.Evaluate()
        if units == "seconds":
            return (arg1 - arg0).seconds
        elif units == "minutes":
            return (arg1 - arg0).minutes
        elif units == "hours":
            return (arg1 - arg0).hours
        elif units == "days":
            return (arg1 - arg0).days
        elif units == "weeks":
            return (arg1 - arg0).days / 7
        elif units == "months":
            return (arg1 - arg0).days / 30
        elif units == "years":
            return (arg1 - arg0).days / 365
        else:
            ValueErr("Invalid units", *arg1.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def Day(runtime, arg0):
        return arg0.Evaluate() == datetime.now().day
        # Done

    @validate_params
    @staticmethod
    def DayOfWeek(runtime, arg0):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[datetime.now().isoweekday()] == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def DecideEdge(runtime):
        if random.randint(0, 1) == 0:
            return Dispatch.vocab("#HoldTheEdge")
        else:
            return Dispatch.vocab("#StopStrokingEdge")
        # Done

    @validate_params
    @staticmethod
    def DecideOrgasm(runtime, arg0, arg1, arg2):
        chance_map = {1: 100, 2: 75, 3: 50, 4: 20, 5: 0}
        if runtime.context == "end":
            if random.randint(0, 100) < chance_map[runtime.settings.Domme.allows_orgasms]:
                Dispatch.Goto(arg0 or StringToken(*runtime.get_position(), "Orgasm Allow"))
            else:
                if random.randint(0, 100) < chance_map[runtime.settings.Domme.ruins_orgasms]:
                    Dispatch.Goto(arg1 or StringToken(*runtime.get_position(), "Orgasm Ruin"))
                else:
                    Dispatch.Goto(arg2 or StringToken(*runtime.get_position(), "Orgasm Deny"))
        else:
            SyntaxErr("@DecideOrgasm is only allowed in end scripts", *runtime.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def DecreaseOrgasmChance(runtime):
        runtime.settings.Domme.AllowsOrgasm -= 1
        # Done

    @validate_params
    @staticmethod
    def DecreaseRuinChance(runtime):
        runtime.settings.Domme.RuinsOrgasms -= 1
        # Done

    @validate_params
    @staticmethod
    def DeleteFlag(runtime, arg0):
        flag = arg0.Evaluate()
        if flag in runtime._temp_flags:
            runtime._temp_flags.remove(flag)
        filepath = os.path.join(runtime.flag_path, flag)
        if os.path.isfile(filepath):
            os.remove(filepath)
        # Done

    @validate_params
    @staticmethod
    def DeleteLocalImage(runtime, arg0):
        if not runtime.settings.AllowDomToDeleteLocalImages:
            return
        if os.path.isfile(arg0.Evaluate()):
            shutil.move(
                runtime.current_image_path,
                os.path.join(APPLICATION_ROOT, "\\DeletedImages\\", os.path.basename(arg0.Evaluate())),
            )
        # Done

    @validate_params
    @staticmethod
    def DeleteVar(runtime, arg0):
        filepath = os.path.join(runtime.var_path, arg0.Evaluate())
        if os.path.isfile(filepath):
            os.remove(filepath)
        # Done

    @validate_params
    @staticmethod
    def DifferentAnswer(runtime):
        pass  # doesn't need an implementation, we just match the string value
        # Done

    @validate_params
    @staticmethod
    def DislikeBlogImage(runtime):
        pass

    @validate_params
    @staticmethod
    def Domme(runtime, arg0):
        return runtime.settings.domme_namespace(arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def DommeAvatarReset(runtime):
        if runtime.domme_avatar_backup:
            runtime.settings.Domme._avatar = runtime.domme_avatar_backup
            runtime.domme_avatar_backup = None
        # Done

    @validate_params
    @staticmethod
    def DommeAvatarTemp(runtime, arg0):
        runtime.domme_avatar_backup = runtime.settings.Domme._avatar
        runtime.settings.Domme._avatar = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def DommeLevel(runtime, *args):
        for arg in args:
            if runtime.settings.Domme.Level == arg.Evaluate():
                return True
        return False
        # Done

    @validate_params
    @staticmethod
    def DommeNameReset(runtime):
        if runtime.domme_name_backup:
            runtime.active_domme = runtime.domme_name_backup
            runtime.domme_name_backup = None
        # Done

    @validate_params
    @staticmethod
    def DommeNameTemp(runtime, arg0):
        runtime.domme_name_backup = runtime.active_domme.name
        runtime.active_domme.name = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def DommeTag(runtime, *args):
        args = [arg.Evaluate() for arg in args]
        if os.path.isdir(runtime.settings.Domme._image_folder):
            if os.path.isfile(os.path.join(runtime.settings.Domme._image_folder, "ImageTags.txt")):
                with open(os.path.join(runtime.settings.Domme._image_folder, "ImageTags.txt"), "r") as f:
                    lines = f.readlines()
                lines = [line.split() for line in lines]
                for line in lines:
                    if (
                        all(args) in line
                        and os.path.join(runtime.settings.Domme._image_folder, line[0]) == runtime._current_image_path
                    ):
                        return True
                return False
        # Done

    @validate_params
    @staticmethod
    def DommeTagAny(runtime, *args):
        args = [arg.Evaluate() for arg in args]
        if os.path.isdir(runtime.settings.Domme._image_folder):
            if os.path.isfile(os.path.join(runtime.settings.Domme._image_folder, "ImageTags.txt")):
                with open(os.path.join(runtime.settings.Domme._image_folder, "ImageTags.txt"), "r") as f:
                    lines = f.readlines()
                lines = [line.split() for line in lines]
                for line in lines:
                    if (
                        any(args) in line
                        and os.path.join(runtime.settings.Domme._image_folder, line[0]) == runtime._current_image_path
                    ):
                        return True
                return False
        # Done

    @validate_params
    @staticmethod
    def Edge(runtime, arg0):
        # TODO: @Edge logic will need to handle transitioning state from "edge" to "normal_hold", "long_hold", "extreme_hold"
        pass

    @validate_params
    @staticmethod
    def EdgeHold(runtime, arg0=None):
        # If present, we map the parameter to user-configured min/max hold time settings and constrain it to those values.
        if arg0:
            duration = convert_string_time_to_seconds(arg0.Evaluate())
            if duration == "invalid units":
                ValueErr("Invalid parameter for @EdgeHold", *arg0.get_position()).throw()
            if duration < runtime.settings.Sub.max_edge_hold_time:
                Dispatch.Edge(StringToken(*arg0.get_position(), "Hold"))
            if (
                duration > runtime.settings.Sub.max_edge_hold_time
                and duration < runtime.settings.Sub.min_extreme_hold_time
            ):
                Dispatch.Edge(StringToken(*arg0.get_position(), "LongHold"))
            if duration > runtime.settings.Sub.max_extreme_hold_time:
                Dispatch.Edge(StringToken(*arg0.get_position(), "ExtremeHold"))
        else:
            Dispatch.Edge(StringToken(*runtime.get_position(), "Hold"))
        # Done

    @validate_params
    @staticmethod
    def EdgeHoldKeyword(runtime):
        return Dispatch.vocab("#EdgeHold")
        # Done

    @validate_params
    @staticmethod
    def EdgeMode(runtime, arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @EdgeMode must be one of 'video' or 'goto'", *arg0.get_position()
            )
        runtime.mode = CustomMode(runtime, mode, arg1, "edge")

    @validate_params
    @staticmethod
    def Edging(runtime):
        return runtime._taunt_context == "edge"
        # Done

    @validate_params
    @staticmethod
    def EmoteMessage(runtime):
        runtime.emote_message = True
        # Done

    @validate_params
    @staticmethod
    def End(runtime):
        if runtime._context == "link" and runtime._bookmark_link:
            runtime._bookmark_link = False
            runtime.pointer += 1
            # TODO: select module and @CallReturn it
            return
        if runtime._context == "module" and runtime._bookmark_module:
            runtime._bookmark_module = False
            runtime.pointer += 1
            # What do we do if runtime.tease_time <= 0?
            # To align with our policy of respecting user settings over scripts when there is a conflict, we should
            # probably end the tease
            # TODO: advance interpreter pointer? and select link and @CallReturn it
            return
        path = runtime.get_position[2]  # grab the path for the current script
        runtime.pointer = 0  # move to the top of the stack
        found_start = False
        while runtime.pointer <= len(runtime.blocks) - 1:
            if runtime.blocks[runtime.pointer].get_position()[2] == path:
                if not found_start:
                    found_start = True  # set True the first time we encounter a block from the script we're removing
                runtime.blocks.pop(runtime.pointer)
            elif found_start:
                break  # we've found the end of the script file we're removing, and the pointer is in the right position
            else:
                runtime.pointer += 1  # we haven't found the start of the script yet
        match runtime._context:
            case "start":
                runtime._context = "link"
                # TODO: select link file and @Call it
            case "link":
                runtime._context = "module"
                # TODO: select module file and @Call it
            case "module":
                if runtime.tease_time <= 0:
                    # TODO: select end script and @Call it
                    return
                runtime._context = "link"
                # TODO: select link file and @Call it
            case "interrupt":
                runtime._context = runtime._previous_context
                # here, the stack should handle resuming where we left off.
        # NFI

    @validate_params
    @staticmethod
    def EndTease(runtime):
        Bus.emit("end_tease")
        # Done

    @validate_params
    @staticmethod
    def ExpireFlag(runtime, arg0, arg1):
        filename = arg0.Evaluate()
        if not is_valid_filename(filename):
            ValueErr("Invalid filename specified for @ExpireFlag", *arg0.get_position()).throw()
        time = convert_string_time_to_seconds(arg1.Evaluate())
        date = datetime.now() + timedelta(seconds=time)
        with open(os.path.join(runtime.var_path, filename), "w") as f:
            f.write(date)
        # Done

    @validate_params
    @staticmethod
    def ExtremeHold(runtime):
        pass

    @validate_params
    @staticmethod
    def ExtremeHoldKeyword(runtime):
        return Dispatch.vocab("#ExtremeHold")
        # Done

    @validate_params
    @staticmethod
    def ExtremeTaunt(runtime):
        return runtime.context == "extreme_hold"
        # Done

    @validate_params
    @staticmethod
    def FirstRound(runtime):
        return runtime.round == 1
        # Done

    @validate_params
    @staticmethod
    def Flag(runtime, arg0):
        flag = arg0.Evaluate()
        if flag in runtime._temp_flags:
            return True
        return os.path.isfile(os.path.join(runtime.flag_path, flag))
        # Done

    @validate_params
    @staticmethod
    def FlagOr(runtime, *args):
        return any([Dispatch.Flag(arg) for arg in args])
        # Done

    @validate_params
    @staticmethod
    def FollowUp(runtime, arg0, arg1):
        if random.randint(0, 100) < arg0.Evaluate():
            runtime.generic_visit(arg1)
        # Done

    @validate_params
    @staticmethod
    def GeneralTime(runtime):
        return Dispatch.vocab("#GeneralTime")
        # Done

    @validate_params
    @staticmethod
    def GoodAfternoonSub(runtime):
        return Dispatch.vocab("#GoodAfternoonSub")
        # Done

    @validate_params
    @staticmethod
    def GoodEveningSub(runtime):
        return Dispatch.vocab("#GoodEveningSub")
        # Done

    @validate_params
    @staticmethod
    def GoodMood(runtime):
        return runtime.domme_mood >= runtime.settings.Domme.mood_index_max
        # Done

    @validate_params
    @staticmethod
    def GoodMorningSub(runtime):
        return Dispatch.vocab("#GoodMorningSub")
        # Done

    @register("Goto")
    @validate_params
    @staticmethod
    def Goto(runtime, arg0):
        headline = arg0.Evaluate()
        path = arg0.get_position()[2]
        looped = False
        while True:
            block = runtime.blocks[runtime.pointer]
            if not isinstance(block, HeadlineToken):
                if block.get_position()[2] == path:
                    runtime.pointer += 1
                elif looped:
                    SyntaxErr(f"@Goto headline ({headline}) not found", *runtime.get_position()).throw()
                else:
                    runtime.pointer = 0
                    looped = True
                    while runtime.blocks[runtime.pointer].get_position()[2] != path:
                        runtime.pointer += 1
            else:
                if block.value == headline:
                    break
        # Done

    @validate_params
    @staticmethod
    def GotoDommeApathy(runtime):
        level = ""
        match runtime.settings.Domme.ApathyLevel:
            case 1:
                level = "ApathyLevel1"
            case 2:
                level = "ApathyLevel2"
            case 3:
                level = "ApathyLevel3"
            case 4:
                level = "ApathyLevel4"
            case 5:
                level = "ApathyLevel5"
        Dispatch.Goto(StringToken(*runtime.get_position(), level))

    # Done

    @validate_params
    @staticmethod
    def GotoDommeLevel(runtime):
        level = ""
        match runtime.settings.Domme.Level:
            case 1:
                level = "DommeLevel1"
            case 2:
                level = "DommeLevel2"
            case 3:
                level = "DommeLevel3"
            case 4:
                level = "DommeLevel4"
            case 5:
                level = "DommeLevel5"
        Dispatch.Goto(StringToken(*runtime.get_position(), level))

    # Done

    @validate_params
    @staticmethod
    def GotoDommeOrgasm(runtime):
        Dispatch.Goto(StringToken(*runtime.get_position(), runtime.settings.Domme.allows_orgasms_string))

    # Done

    @validate_params
    @staticmethod
    def GotoDommeRuin(runtime):
        Dispatch.Goto(StringToken(*runtime.get_position(), runtime.settings.Domme.ruins_orgasm_string))

    # Done

    @validate_params
    @staticmethod
    def GreetSub(runtime):
        return Dispatch.vocab("#GreetSub")
        # Done

    @validate_params
    @staticmethod
    def Group(runtime, arg0):
        members = arg0.Evaluate().split("")
        return all([member in runtime._present for member in members])
        # Done

    @validate_params
    @staticmethod
    def GroupContains(runtime, arg0):
        members = arg0.Evaluate().split("")
        return any([member in runtime._present for member in members])
        # Done

    @validate_params
    @staticmethod
    def HentaiImageCount(runtime):
        if os.path.isdir(runtime.settings.hentai_images):
            return len(os.listdir(runtime.settings.hentai_images))
        return 0
        # Done

    @validate_params
    @staticmethod
    def HideChatMessage(runtime):
        runtime.hide_chat_message = True
        # Done

    @validate_params
    @staticmethod
    def HoldTaunt(runtime):
        return runtime.context == "normal_hold"
        # Done

    @validate_params
    @staticmethod
    def HoldingTheEdge(runtime):
        return runtime.holding_state
        # Done

    @validate_params
    @staticmethod
    def ImageBarOff(runtime, arg0, arg1):
        pass

    @validate_params
    @staticmethod
    def ImageBarOn(runtime, arg0, arg1, arg2, arg3, arg4, arg5):
        pass

    @validate_params
    @staticmethod
    def ImageTag(runtime, *args):
        Bus.emit("show_image_tag", [arg.Evaluate() for arg in args])
        # Done

    @validate_params
    @staticmethod
    def ImageTagAny(runtime, *args):
        Bus.emit("show_image_tag_any", [arg.Evaluate() for arg in args])
        # Done

    @validate_params
    @staticmethod
    def InChastity(runtime):
        return runtime.in_chastity
        # Done

    @validate_params
    @staticmethod
    def IncreaseOrgasmChance(runtime):
        runtime.settings.Domme.allows_orgasms += 1
        # Done

    @validate_params
    @staticmethod
    def IncreaseRuinChance(runtime):
        runtime.settings.Domme.ruins_orgasms += 1
        # Done

    @validate_params
    @staticmethod
    def InputVar(runtime, arg0):
        filename = arg0.Evaluate()
        if not is_valid_filename(filename):
            ValueErr("Invalid filename specified for @InputVar", *arg0.get_position()).throw()

        def input_var_handler(runtime, sender, message):
            if isinstance(message, UserMessage):
                with open(os.path.join(runtime.var_path, filename), "w") as f:
                    f.write(message.text)
                Bus.unsub("new_message", input_var_handler)

        Bus.sub("new_message", input_var_handler)
        # Done

    @validate_params
    @staticmethod
    def Interrupt(runtime, arg0):
        if runtime.interrupt_state:
            runtime._previous_context = runtime._context
            runtime._context = "interrupt"
            Dispatch.CallReturn(arg0)
        # Done

    @validate_params
    @staticmethod
    def InterruptLongEdge(runtime):
        pass

    @validate_params
    @staticmethod
    def Interrupts(runtime, arg0):
        runtime.settings.interrupt_state = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def LastJoined(runtime):
        return runtime.last_joined
        # Done

    @validate_params
    @staticmethod
    def LikeBlogImage(runtime):
        pass

    @validate_params
    @staticmethod
    def LikedImageCount(runtime):
        path = os.path.join(APPLICATION_ROOT, "\\Liked Images\\")
        return sum([1 for _ in os.listdir(path)])
        # Done

    @validate_params
    @staticmethod
    def LockMedia(runtime):
        runtime.media_locked = True
        # Done

    @validate_params
    @staticmethod
    def LongEdge(runtime):
        threshold = (
            runtime.settings.Sub.avg_edge_time
            if runtime.settings.Sub.use_avg_as_threshold
            else runtime.settings.Sub.long_edge_threshold * 60
        )
        if runtime.settings._edge_start is not None:
            delta_time = datetime.now() - runtime.settings._edge_start
            if delta_time.seconds > threshold:
                return True
        return False
        # Done

    @validate_params
    @staticmethod
    def LongHold(runtime):
        return Dispatch.vocab("#LongHold")
        # Done

    @validate_params
    @staticmethod
    def LongTaunt(runtime):
        return runtime.context == "long_hold"
        # Done

    @validate_params
    @staticmethod
    def LoopAnswer(runtime):
        runtime._loop_answer = True
        # Done

    @validate_params
    @staticmethod
    def Month(runtime, arg0):
        return arg0.Evaluate() == datetime.now().month
        # Done

    @validate_params
    @staticmethod
    def Mood(runtime, arg0):
        return runtime.domme_mood == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def Morning(runtime):
        return datetime.now().hour > 6 and datetime.now().hour < 12
        # Done

    @validate_params
    @staticmethod
    def MultipleEdges(runtime, arg0, arg1, arg2):
        pass

    @validate_params
    @staticmethod
    def NewContactSlideshow(runtime, arg0):
        dir = runtime.settings.contact_namespace(arg0.Evaluate(), "_image_folder")
        if os.path.isdir(dir):
            folders = [f for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]
            if len(folders) > 0:
                folder = random.choice(folders)
                Bus.emit("new_slideshow", folder)
        else:
            ValueErr("Invalid directory passed to @NewContactSlideshow", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def NewDommeSlideshow(runtime):
        dir = runtime.settings.Domme._image_folder
        if os.path.isdir(dir):
            folders = [f for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]
            if len(folders) > 0:
                folder = folders[random.randint[0, len(folders) - 1]]
                runtime._slides_dir = folder
                slides = [f for f in os.listdir(os.path.join(dir, folder)) if is_image_file(f)]
                runtime._slides = [os.path.join(dir, folder, f) for f in slides]
                Bus.emit("new_slideshow", folder)
        else:
            ValueErr("Invalid directory passed to @NewDommeSlideshow", 0, 0, "").throw()
        # Done

    @validate_params
    @staticmethod
    def Night(runtime):
        return datetime.now().hour > 19 or datetime.now().hour < 6
        # Done

    @validate_params
    @staticmethod
    def NoMode(runtime, arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @NoMode must be one of 'video' or 'goto'", *arg0.get_position()
            )
        runtime.mode = CustomMode(runtime, mode, arg1, "no")
        # Done

    @validate_params
    @staticmethod
    def Null(runtime):
        return ""
        # Done

    @validate_params
    @staticmethod
    def NullNextDommeImage(runtime):
        runtime.null_domme_image = True
        # Done

    @validate_params
    @staticmethod
    def OrgasmAllow(runtime):
        # What happens in this case if orgasm_restricted is True?
        # Executive decision: This is a problem with the script, not the interpreter, so we throw an error and die.
        if not runtime.orgasm_restricted:
            runtime.orgasm_allowed = True
            Dispatch.Goto(StringToken(*runtime.get_position(), "Orgasm Allow"))
        else:
            RuntimeErr(
                "@OrgasmAllow cannot be called while @OrgasmRestricted is in effect.", *runtime.get_position()
            ).throw()
        # Done

    @validate_params
    @staticmethod
    def OrgasmAllowed(runtime):
        return runtime.orgasm_allowed
        # Done

    @validate_params
    @staticmethod
    def OrgasmDenied(runtime):
        return runtime.orgasm_denied
        # Done

    @validate_params
    @staticmethod
    def OrgasmDeny(runtime):
        runtime.orgasm_denied = True
        Dispatch.Goto(StringToken(*runtime.get_position(), "Orgasm Deny"))
        # Done

    @validate_params
    @staticmethod
    def OrgasmLockDate(runtime):
        return runtime.settings.orgasm_lock_date
        # Done

    @validate_params
    @staticmethod
    def OrgasmRestricted(runtime):
        return runtime.orgasm_restricted
        # Done

    @validate_params
    @staticmethod
    def OrgasmRuin(runtime):
        runtime.orgasm_ruined = True
        Dispatch.Goto(StringToken(*runtime.get_position(), "Orgasm Ruin"))
        # Done

    @validate_params
    @staticmethod
    def OrgasmRuined(runtime):
        return runtime.orgasm_ruined
        # Done

    @validate_params
    @staticmethod
    def PaceFastest(runtime):
        pace = {}
        Bus.emit("get_metro_pace", pace)
        return pace["pace"] == 120
        # Done

    @validate_params
    @staticmethod
    def PaceSlowest(runtime):
        pace = {}
        Bus.emit("get_metro_pace", pace)
        return pace["pace"] == 30
        # Done

    @validate_params
    @staticmethod
    def PauseVideo(runtime):
        Bus.emit("pause_video")
        # Done

    @validate_params
    @staticmethod
    def PetName(runtime):
        if runtime.petname_temp != "":
            return runtime.petname_temp
        names = []
        mood = runtime.domme_mood
        if mood <= runtime.settings.Domme.MoodIndexMin:
            names = runtime.settings.Domme.BadMoodPetNames
        if mood > runtime.settings.Domme.MoodIndexMin and mood < runtime.settings.Domme.MoodIndexMax:
            names = runtime.settings.Domme.NeutralMoodPetNames
        if mood >= runtime.settings.Domme.MoodIndexMax:
            names = runtime.settings.Domme.GoodMoodPetNames
        return names[random.randint(0, len(names) - 1)]
        # Done

    @validate_params
    @staticmethod
    def PetNameReset(runtime):
        runtime.petname_temp = ""
        # Done

    @validate_params
    @staticmethod
    def PetNameTemp(runtime, arg0):
        runtime.petname_temp = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def PlayAudio(runtime, arg0):
        Bus.emit("play_audio", arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def PlayAudioLoop(runtime, arg0, arg1):
        Bus.emit("play_audio_loop", arg0.Evaluate(), arg1.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def PlayAvoidTheEdge(runtime):
        Dispatch.CallReturn(
            StringToken(
                *runtime.get_position(), os.path.join(runtime.game_path, "\\Avoid The Edge\\Avoid The Edge.txt")
            )
        )
        # Done

    @validate_params
    @staticmethod
    def PlayCensorshipSucks(runtime):
        Dispatch.CallReturn(
            StringToken(
                *runtime.get_position(), os.path.join(runtime.game_path, "\\Censorship Sucks\\Censorship Sucks.txt")
            )
        )
        # Done

    @validate_params
    @staticmethod
    def PlayDommeGenreVideo(runtime, arg0):
        genre = arg0.Evaluate()
        dir = runtime.settings.domme_namespace(genre + "_video")
        video = random_video(dir)
        Dispatch._registry["PlayVideo"](StringToken(*arg0.get_position(), video))
        # Done

    @validate_params
    @staticmethod
    def PlayGenreVideo(runtime, arg0):
        genre = arg0.Evaluate()
        dir = getattr(runtime.settings, genre + "_video")
        video = random_video(dir)
        Dispatch._registry["PlayVideo"](StringToken(*arg0.get_position(), video))
        # Done

    @validate_params
    @staticmethod
    def PlayRedLightGreenLight(runtime):
        Dispatch.CallReturn(
            StringToken(
                *runtime.get_position(),
                os.path.join(runtime.game_path, "\\Red Light Green Light\\Red Light Green Light.txt"),
            )
        )
        # Done

    @validate_params
    @staticmethod
    def PlayRiskyPick(runtime):
        if os.path.isfile(os.path.join(runtime.game_path, "\\Risky Pick Replacement\\Risky Pick 2026.txt")):
            Dispatch.CallReturn(
                StringToken(
                    *runtime.get_position(),
                    os.path.join(runtime.game_path, "\\Risky Pick Replacement\\Risky Pick 2026.txt"),
                )
            )
        else:
            Dispatch.CallReturn(
                StringToken(
                    0, 0, "", os.path.join(runtime.game_path, "\\Risky Pick Replacement\\Risky Pick Replacement.txt")
                )
            )
        # Done

    @register("PlayVideo")
    @validate_params
    @staticmethod
    def PlayVideo(runtime, arg0=None, arg1=None):
        if arg0 is None:
            files = []
            folders = [
                runtime.settings.blowjob_video,
                runtime.settings.ch_video,
                runtime.settings.joi_video,
                runtime.settings.hardcore_video,
                runtime.settings.softcore_video,
                runtime.settings.lesbian_video,
                runtime.settings.femdom_video,
                runtime.settings.femsub_video,
                runtime.settings.general_video,
            ]
            for folder in [folder for folder in folders if folder != "" and os.path.isdir(folder)]:
                files.extend(os.listdir(folder))
            if len(files) > 0:
                files = [file for file in files if is_video_file(file)]
            else:
                return
            if len(files) > 0:
                if arg1 is None:
                    Bus.emit("play_video", random.choice(files))
                else:
                    Bus.emit("play_audio", random.choice(files), arg1.Evaluate())
        if arg0 is not None:
            if is_video_file(arg0.Evaluate()):
                if arg1 is None:
                    Bus.emit("play_video", arg0.Evaluate())
                else:
                    Bus.emit("play_video", arg0.Evaluate(), arg1.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def RT(runtime, *args):
        return random.choice(args).Evaluate()
        # Done

    @validate_params
    @staticmethod
    def Random(runtime, arg0, arg1, arg2=None):
        num = random.randint(arg0.Evaluate(), arg1.Evaluate())
        if arg2 is not None:
            return round(num / arg2.Evaluate()) * arg2.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def RandomContact(runtime):
        contact = random.choice(runtime._present)
        runtime.active_domme = runtime.settings.contact_namespace(contact, "name")
        # Done

    @validate_params
    @staticmethod
    def RapidText(runtime, arg0):
        runtime.rapid_text = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def RarelyAllowsOrgasm(runtime):
        return runtime.settings.Domme.allows_orgasms == 4
        # Done

    @validate_params
    @staticmethod
    def RarelyRuinsOrgasm(runtime):
        return runtime.settings.Domme.ruins_orgasms == 4
        # Done

    @validate_params
    @staticmethod
    def RemoveContact(runtime, arg0):
        runtime._present.remove(arg0.Evaluate())
        if not runtime.hide_chat:
            Bus.emit("new_message", SystemMessage(f"{runtime.settings.id_to_name(arg0.Evaluate())} has logged out."))
        # Done

    @validate_params
    @staticmethod
    def RemoveDomme(runtime):
        runtime._present.remove("D")
        if not runtime.hide_chat:
            Bus.emit("new_message", SystemMessage(f"{runtime.settings.Domme.name} has logged out."))
        # Done

    @validate_params
    @staticmethod
    def RemoveEdgeHoldTime(runtime, arg0=None, arg1=None):
        if arg0 is None and arg1 is None:
            min = runtime.settings.Sub.min_edge_hold_time
            max = runtime.settings.Sub.max_edge_hold_time
            runtime.edge_hold_time -= random.randint(min, max)
        if isinstance(arg0, IntegerToken):
            min = arg0.Evaluate()
            if arg1 is None:
                runtime.edge_hold_time -= min
            elif isinstance(arg1, IntegerToken):
                runtime.edge_hold_time -= random.randint(min, arg1.Evaluate())
            else:
                max = convert_string_time_to_seconds(arg1.Evaluate())
                if max == "invalid units":
                    ValueErr(
                        f"Got invalid parameter {arg1.Evaluate()} for @RemoveEdgeHoldTime", *arg1.get_position()
                    ).throw()
                runtime.edge_hold_time -= random.randint(min, max)
        if isinstance(arg0, StringToken):
            min = convert_string_time_to_seconds(arg0.Evaluate())
            if min == "inavalid units":
                ValueErr(
                    f"Got invalid parameter {arg0.Evaluate()} for @RemoveEdgeHoldTime", *arg0.get_position()
                ).throw()
            if arg1 is None:
                runtime.edge_hold_time -= min
            elif isinstance(arg1, IntegerToken):
                runtime.edge_hold_time -= random.randint(min, arg1.Evaluate())
            elif isinstance(arg1, StringToken):
                max = convert_string_time_to_seconds(arg1.Evaluate())
                if max == "invalid units":
                    ValueErr(f"Got invalid parameter {arg1.Evaluate()}", *arg0.get_position()).throw()
                runtime.edge_hold_time -= random.randint(min, max)
        if runtime.edge_hold_time <= 0:
            runtime.edge_hold_time = 0
            Bus.emit("stop_hold")
        # Done

    @validate_params
    @staticmethod
    def RemoveStrokeTime(runtime, arg0, arg1):
        if arg0 is None and arg1 is None:
            min = runtime.settings.taunt_cycle_min
            max = runtime.settings.taunt_cycle_max
            runtime.stroke_time -= random.randint(min, max)
        if isinstance(arg0, IntegerToken):
            min = arg0.Evaluate()
            if arg1 is None:
                runtime.stroke_time -= min
            elif isinstance(arg1, IntegerToken):
                runtime.stroke_time -= random.randint(min, arg1.Evaluate())
            else:
                max = convert_string_time_to_seconds(arg1.Evaluate())
                if max == "invalid units":
                    ValueErr(
                        f"Got invalid parameter {arg1.Evaluate()} for @RemoveEdgeHoldTime", *arg1.get_position()
                    ).throw()
                runtime.stroke_time -= random.randint(min, max)
        if isinstance(arg0, StringToken):
            min = convert_string_time_to_seconds(arg0.Evaluate())
            if min == "inavalid units":
                ValueErr(
                    f"Got invalid parameter {arg0.Evaluate()} for @RemoveEdgeHoldTime", *arg0.get_position()
                ).throw()
            if arg1 is None:
                runtime.stroke_time -= min
            elif isinstance(arg1, IntegerToken):
                runtime.stroke_time -= random.randint(min, arg1.Evaluate())
            elif isinstance(arg1, StringToken):
                max = convert_string_time_to_seconds(arg1.Evaluate())
                if max == "invalid units":
                    ValueErr(f"Got invalid parameter {arg1.Evaluate()}", *arg0.get_position()).throw()
                runtime.stroke_time -= random.randint(min, max)
        if runtime.stroke_time <= 0:
            runtime.stroke_time = 0
            Bus.emit("stop_stroking")
        # Done

    @validate_params
    @staticmethod
    def RemoveTeaseTime(runtime, arg0=None, arg1=None):
        if arg0 is None:
            min = runtime.settings.min_tease_length
            runtime.tease_time -= random.randint(min, runtime.tease_time)
        min = convert_string_time_to_seconds(arg0.Evaluate())
        if min == "invalid units":
            ValueErr("Got invalid parameter for @RemoveTeaseTime", *arg0.get_position()).throw()
        if arg1 is None:
            runtime.tease_time -= min
        else:
            max = convert_string_time_to_seconds(arg1.Evaluate())
            if max == "invalid units":
                ValueErr("Got invalid parameter for @RemoveTeaseTime", *arg1.get_position()).throw()
            runtime.tease_time -= random.randint(min, max)
        if runtime.tease_time <= 0:
            Bus.emit("end_tease")
        # NFI: Probably need to call an end script here and exit gracefully rather than just call end_tease

    @validate_params
    @staticmethod
    def ResponseNo(runtime, arg0):
        if os.path.isfile(arg0.Evaluate()):
            runtime._response_no = True
            runtime._response_script = arg0.Evaluate()
        else:
            RuntimeErr(f"Script: {arg0.Evalute()} not found", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def ResponseYes(runtime, arg0):
        if os.path.isfile(arg0.Evaluate()):
            runtime._response_yes = True
            runtime._response_script = arg0.Evaluate()
        else:
            RuntimeErr(f"Script: {arg0.Evalute()} not found", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def RestrictOrgasm(runtime, arg0, arg1):
        runtime.orgasm_restricted = True
        # Done

    @validate_params
    @staticmethod
    def RuinYourOrgasm(runtime):
        return Dispatch.vocab("#RuinYourOrgasm")
        # Done

    @validate_params
    @staticmethod
    def RuinedMode(runtime, arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @RuinedMode must be one of 'video' or 'goto'",
                *arg0.get_position(),
            )
        runtime.mode = CustomMode(runtime, mode, arg1, "ruined")
        # Done

    @validate_params
    @staticmethod
    def RuinsOrgasm(runtime):
        return runtime.settings.Domme.ruins_orgasms != 5
        # Done

    @validate_params
    @staticmethod
    def SYS_MultipleEdgesStart(runtime):
        return Dispatch.vocab("#SYS_MultipleEdgesStart")
        # Done

    @validate_params
    @staticmethod
    def Sadistic(runtime):
        return runtime.settings.Domme.sadistic
        # Done

    @validate_params
    @staticmethod
    def SelfOld(runtime):
        return runtime.settings.Domme.age > 50
        # Done

    @validate_params
    @staticmethod
    def SelfYoung(runtime):
        return runtime.settings.Domme.age < 30
        # Done

    @validate_params
    @staticmethod
    def SendDailyTasks(runtime):
        pass

    @validate_params
    @staticmethod
    def Session(runtime, arg0):
        return getattr(runtime, arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def SessionCBTBalls(runtime):
        return runtime.cbt_balls
        # Done

    @validate_params
    @staticmethod
    def SessionEdges(runtime):
        return runtime.edges
        # Done

    @validate_params
    @staticmethod
    def SetDate(runtime, arg0, arg1):
        var_file = os.path.join(runtime.var_path, arg0.Evaluate)
        if not is_valid_filename(var_file):
            ValueErr("Invalid filename specified for @SetDate", *arg0.get_position()).throw()
        delta = convert_string_time_to_seconds(arg1.Evaluate())
        if delta == "invalid units":
            SyntaxErr("Invalid units specified for time delta", *arg1.get_position()).throw()
        date = datetime.now() + timedelta(0, delta)
        with open(var_file, "w") as f:
            f.write(date)
        # Done

    @validate_params
    @staticmethod
    def SetDomme(runtime, arg0):
        if arg0.Evaluate() == "D":
            runtime.active_domme = runtime.settings.Domme.name
        elif arg0.Evaluate() >= 1 and arg0.Evaluate() <= 6:
            runtime.active_domme = runtime.settings.contact_namespace(arg0.Evaluate(), "name")
        else:
            ValueErr("Got invalid parameter for @SetDomme", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def SetFlag(runtime, arg0):
        flag = arg0.Evaluate()
        if not is_valid_filename(flag):
            ValueErr("Invalid filename specified for @SetFlag", *arg0.get_position()).throw()
        with open(os.path.join(runtime.flag_path, flag), "w") as f:
            f.write("")
        # NFI Need to make sure the string is a valid Windows filename

    @validate_params
    @staticmethod
    def SetImageBarImage(runtime, arg0, arg1):
        pass

    @validate_params
    @staticmethod
    def SetLink(runtime, arg0, arg1=None):
        # runtime._next_link expects a 2-tuple of the form (int: line_number OR string: headline, string: filename)
        filepath = os.path.join(runtime.stroke_path, "Link", arg0.Evaluate())
        if os.path.isfile(filepath):
            runtime._next_link = (0 if arg1 is None else arg1.Evaluate(), filepath)
            return
        filepath = os.path.join(runtime.custom_path, "Link", arg0.Evaluate())
        if os.path.isfile(filepath):
            runtime._next_link = (0 if arg1 is None else arg1.Evaluate(), filepath)
        # NFI ensure we check for these when choosing the next link file

    @validate_params
    @staticmethod
    def SetModule(runtime, arg0, arg1=None):
        # runtime._next_module expects a 2-tuple of the form (int: line_number OR string: headline, string: filename)
        filepath = os.path.join(runtime.stroke_path, "Modules", arg0.Evaluate())
        if os.path.isfile(filepath):
            runtime._next_module = (0 if arg1 is None else arg1.Evaluate(), filepath)
            return
        filepath = os.path.join(runtime.custom_path, "Modules", arg0.Evaluate())
        if os.path.isfile(filepath):
            runtime._next_module = (0 if arg1 is None else arg1.Evaluate(), filepath)
        # NFI Ensure we check for these when choosing the next module to run

    @validate_params
    @staticmethod
    def SetMood(runtime, arg0):
        runtime.domme_mood = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def Settings(runtime, arg0):
        return getattr(runtime.settings, arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def ShortName(runtime):
        return runtime.settings.Domme.short_name
        # Done

    @validate_params
    @staticmethod
    def ShowBlogImage(runtime):
        pass

    @validate_params
    @staticmethod
    def ShowDislikedImage(runtime):
        dir = os.path.join(APPLICATION_ROOT, "Disliked Images\\")
        files = []
        if os.path.isdir(dir):
            files = [file for file in os.listdir(dir) if is_image_file(file)]
        TypeErr(f"{dir} is not a valid directory", 0, 0, "").throw()
        if len(files) > 0:
            Bus.emit("show_image", random.choice(files))
        # Done

    @validate_params
    @staticmethod
    def ShowImage(runtime, arg0):
        if is_image_file(arg0.Evaluate()):
            Bus.emit("show_image", arg0.Evaluate())
        else:
            TypeErr(f"{arg0.Evaluate()} is not a valid image file", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def ShowLikedImage(runtime):
        dir = os.path.join(APPLICATION_ROOT, "Liked Images\\")
        files = []
        if os.path.isdir(dir):
            files = [file for file in os.listdir(dir) if is_image_file(file)]
        else:
            TypeErr(f"{dir} is not a valid directory", 0, 0, "").throw()
        if len(files) > 0:
            Bus.emit("show_image", random.choice(files))
        # Done

    @validate_params
    @staticmethod
    def ShowNotTaggedImage(runtime):
        dir = runtime._slides_dir
        files = [file for file in os.listdir(dir) if is_image_file(file)]
        if not os.path.isfile(os.path.join(dir, "ImageTags.txt")):
            Bus.emit("show_image", random.choice(files))
        else:
            imgs = []
            tag_imgs = []
            with open(os.path.join(dir, "ImageTags.txt"), "r") as f:
                lines = f.readlines()
                for line in lines:
                    tags = line.split()
                    tag_imgs.append(tags[0])
                    if len(tags) == 1:
                        imgs.append(tags[0])
                imgs.extend([file for file in files if file not in tag_imgs])
                Bus.emit("show_image", random.choice(imgs))
        # Done

    @validate_params
    @staticmethod
    def ShowTaggedImage(runtime):
        dir = runtime._slides_dir
        tag_imgs = []
        if os.path.isfile(os.path.join(dir, "ImageTags.txt")):
            with open(os.path.join(dir, "ImageTags.txt"), "r") as f:
                lines = f.readlines()
            for line in lines:
                tags = line.split()
                if len(tags) > 1:
                    tag_imgs.append[tags[0]]
            Bus.emit("show_image", random.choice(tag_imgs))
        # Done

    @validate_params
    @staticmethod
    def ShowWait(runtime):
        pass

    @validate_params
    @staticmethod
    def Slideshow(runtime, arg0, arg1=None, arg2=None):
        paths = []
        if path1 := getattr(runtime.settings, f"{arg0.Evaluate().lower()}_images"):
            paths.append(path1)
            if arg1 is not None:
                if path2 := getattr(runtime.settings, f"{arg1.Evaluate().lower()}_images"):
                    paths.append(path2)
                elif arg1 and arg1.Evaluate().lower() in ("fast", "slow"):
                    pass
                elif arg1:
                    ValueErr("Unrecognized genre specified for @Slideshow", *arg1.get_position()).throw()
        else:
            ValueErr("Unrecognized genre specified for @Slideshow", *arg0.get_position()).throw()
        if all([os.path.isdir(path) for path in paths]):
            slides = [file for file in [os.listdir(path) for path in paths] if is_image_file(file)]
        if len(slides) == 0:
            ValueErr("No image files found for the specified genre(s)", *arg0.get_position()).throw()
        else:
            Bus.emit("new_slideshow", paths)
        # Done

    @validate_params
    @staticmethod
    def SlideshowOff(runtime):
        Bus.emit("stop_slideshow")
        # Done

    @validate_params
    @staticmethod
    def SlideshowOn(runtime):
        Bus.emit("start_slideshow")
        # Done

    @validate_params
    @staticmethod
    def SlideshowPause(runtime):
        Bus.emit("pause_slideshow")
        # Done

    @validate_params
    @staticmethod
    def SlowMotion(runtime, arg0):
        Bus.emit("start_slowmo")
        # Done

    @validate_params
    @staticmethod
    def SometimesAllowsOrgasm(runtime):
        return runtime.settings.Domme.allows_orgasms == 3
        # Done

    @validate_params
    @staticmethod
    def SometimesRuinsOrgasm(runtime):
        return runtime.settings.Domme.ruins_orgasms == 3
        # Done

    @validate_params
    @staticmethod
    def StartStroking(runtime):
        Bus.emit("start_stroking")
        # Done

    @validate_params
    @staticmethod
    def StartStrokingKeyword(runtime):
        return Dispatch.vocab("#StartStroking")
        # Done

    @validate_params
    @staticmethod
    def StopStroking(runtime):
        Bus.emit("stop_stroking")
        # Done

    @validate_params
    @staticmethod
    def StopStrokingKeyword(runtime):
        return Dispatch.vocab("#StopStroking")
        # Done

    @validate_params
    @staticmethod
    def StopStrokingEdge(runtime):
        return Dispatch.vocab("#StopStrokingEdge")
        # Done

    @validate_params
    @staticmethod
    def StopTnA(runtime):
        pass

    @validate_params
    @staticmethod
    def StopVideo(runtime):
        Bus.emit("stop_video")
        # Done

    @validate_params
    @staticmethod
    def StrokeCycleTime(runtime):
        return runtime.stroke_time
        # Done

    @validate_params
    @staticmethod
    def StrokeFaster(runtime):
        Bus.emit("stroke_faster")
        # done

    @validate_params
    @staticmethod
    def StrokeFastest(runtime):
        Bus.emit("stroke_fastest")
        # Done

    @validate_params
    @staticmethod
    def StrokeSlower(runtime):
        Bus.emit("stroke_slower")
        # Done

    @validate_params
    @staticmethod
    def StrokeSlowest(runtime):
        Bus.emit("stroke_slowest")
        # Done

    @validate_params
    @staticmethod
    def Stroking(runtime):
        return runtime._taunt_context == "stroke"
        # Done

    @validate_params
    @staticmethod
    def SubNameReset(runtime):
        runtime.subname_temp = None
        # Done

    @validate_params
    @staticmethod
    def SubNameTemp(runtime, arg0):
        runtime.subname_temp = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def SubName(runtime):
        if runtime.subname_temp is not None:
            return runtime.subname_temp
        return runtime.settings.Sub.name
        # Done

    @validate_params
    @staticmethod
    def SubOld(runtime):
        return runtime.settings.Sub.Age > 50
        # Done

    @validate_params
    @staticmethod
    def SubWritingTaskMax(runtime):
        return runtime.settings.writing_task_lines_max
        # Done

    @validate_params
    @staticmethod
    def SubWritingTaskMin(runtime):
        return runtime.settings.writing_task_lines_min
        # Done

    @validate_params
    @staticmethod
    def SubYoung(runtime):
        return runtime.settings.Sub.Age < 30
        # Done

    @validate_params
    @staticmethod
    def Supremacist(runtime):
        return runtime.settings.Domme.supremacist
        # Done

    @validate_params
    @staticmethod
    def SystemMessage(runtime):
        runtime.system_message = True
        # Done

    @validate_params
    @staticmethod
    def Tag(runtime, *args):
        tags = []
        Bus.emit("img_tags_requested", tags)
        args = list(arg.Evaluate() for arg in args)
        if all(args in tags):
            Bus.emit("dont_advance")
            return True
        return False
        # Done

    @validate_params
    @staticmethod
    def TagAny(runtime, *args):
        tags = []
        Bus.emit("img_tags_requested", tags)
        args = list(arg.Evaluate() for arg in args)
        if any(args in tags):
            Bus.emit("dont_advance")
            return True
        return False
        # Done

    @validate_params
    @staticmethod
    def TagGarment(runtime):
        tags = []
        Bus.emit("img_tags_requested", tags)
        for tag in tags:
            if tag.startswith("TagGarment"):
                return tag[9:]
        # Done

    @validate_params
    @staticmethod
    def TempFlag(runtime, arg0):
        runtime._temp_flags.add(arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def Timeout(runtime, arg0, arg1):
        timeout = arg0.Evaluate()
        timer = Clock.schedule_once(lambda dt: Dispatch.Goto(arg1.Evaluate()), timeout)

        def cancel_timer(runtime, message):
            if isinstance(message, UserMessage):
                timer.cancel()
                Bus.unsub("new_message", cancel_timer)

        Bus.sub("new_message", cancel_timer)
        # Done

    @validate_params
    @staticmethod
    def TnAFastSlides(runtime):
        pass

    @validate_params
    @staticmethod
    def TnAFastSlidesResult(runtime):
        return runtime.tna_fast_slides_result
        # Done

    @validate_params
    @staticmethod
    def TnASlowSlides(runtime):
        pass

    @validate_params
    @staticmethod
    def UnlockMedia(runtime):
        runtime.media_locked = False
        # Done

    @validate_params
    @staticmethod
    def UpdateOrgasm(runtime):
        runtime.settings.Sub.last_orgasm_date = string_from_date(datetime.now())
        # Done

    @validate_params
    @staticmethod
    def UpdateRuined(runtime):
        runtime.settings.Sub.last_ruin_date = string_from_date(datetime.now())
        # Done

    @validate_params
    @staticmethod
    def ValentinesDay(runtime):
        return datetime.now().month == 2 and datetime.now().day == 14
        # Done

    # TODO: It may not be right for this to show up in Dispatch, because these should
    #       be getting turned into VarRef nodes by the tokenizer, whose visit method
    #       doesn't point to Dispatch, but we obviously still want the keyword to be
    #       documented so this requires some thought.
    @validate_params
    @staticmethod
    def Var(runtime, arg0):
        if not is_valid_filename(arg0.Evaluate()):
            ValueErr("Invalid filename specified for #Var", *arg0.get_position()).throw()
        runtime.var_file = arg0.Evaluate()

    @validate_params
    @staticmethod
    def VarExists(runtime, arg0):
        return os.path.isfile(os.path.join(runtime.var_path, arg0.Evaluate()))
        # Done

    @validate_params
    @staticmethod
    def VideoIsPaused(runtime):
        Bus.emit("get_video_info", info := {})
        return info["state"] == "pause"
        # Done

    @validate_params
    @staticmethod
    def VideoIsPlaying(runtime):
        Bus.emit("get_video_info", info := {})
        return info["state"] == "play"
        # Done

    @validate_params
    @staticmethod
    def VideoIsSlowMotion(runtime):
        Bus.emit("get_slowmo_state", info := {"slowmo": None})
        return info["slowmo"]
        # Done

    @validate_params
    @staticmethod
    def VideoLength(runtime):
        Bus.emit("get_video_info", info := {})
        return info["duration"]
        # Done

    @validate_params
    @staticmethod
    def VideoRemaining(runtime):
        Bus.emit("get_video_info", info := {})
        return info["duration"] - info["position"]
        # Done

    @validate_params
    @staticmethod
    def Vulgar(runtime):
        return runtime.settings.Domme.vulgar
        # Done

    @validate_params
    @staticmethod
    def Wait(runtime, arg0):
        Clock.schedule_once(Bus.emit("interpreter_ready"), arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def WaitAudio(runtime):
        Bus.emit("wait_audio", info={"remaining": None})
        Clock.schedule_once(Bus.emit("interpreter_ready"), info["remaining"])
        # Done

    @validate_params
    @staticmethod
    def WhoIsTyping(runtime, arg0):
        return runtime.settings.id_to_name(arg0.Evaluate()) == runtime.active_domme.name
        # Done

    @validate_params
    @staticmethod
    def Worship(runtime, arg0):
        if arg0.Evaluate().lower() in ["ass", "boobs", "feet", "none", "pussy"]:
            if arg0.Evaluate().lower() == "none":
                runtime.worship_mode_target = None
            else:
                runtime.worship_mode_target = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def WorshipOff(runtime):
        pass

    @validate_params
    @staticmethod
    def WorshipOn(runtime):
        pass

    @validate_params
    @staticmethod
    def YesMode(runtime, arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @YesMode must be one of 'video' or 'goto'", *arg0.get_position()
            )
        runtime.mode = CustomMode(runtime, mode, arg1, "yes")
        # Done
