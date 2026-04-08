import os
import random
import shutil
from datetime import datetime, timedelta
from PySide6.QtCore import QTimer
from bus import Bus
from dispatch_dict import DISPATCH_DICT
from message_classes import UserMessage
from tokens import StringToken, IntegerToken
from execution_modes import EdgeTauntCycle
from tai_exceptions import SyntaxErr, TypeErr, ValueErr, RuntimeErr
from custom_mode import CustomMode
from utils import (
    add_time,
    convert_string_time_to_seconds,
    get_settings,
    get_runtime,
    is_image_file,
    random_script,
    date_from_string,
    random_video,
    is_video_file,
    string_from_date,
    is_valid_filename,
)
from slideshow import URL_File

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
    def NOP(*args):
        pass
        # Done

    @validate_params
    @staticmethod
    def AFK(arg):
        Bus.emit("set_AFK", arg.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def AcceptAnswer():
        pass  # doesn't need an implementation, we just match the string value
        # Done

    @validate_params
    @staticmethod
    def AddContact(arg):
        if arg.Evaluate() not in [1, 2, 3, 4, 5, 6]:
            ValueErr("Invalid contact number", *arg.get_position()).throw()
        Bus.emit("add_entity", arg.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def AddDomme():
        Bus.emit("add_entity", "D")
        # Done

    @validate_params
    @staticmethod
    def AddEdgeHoldTime(arg1=None, arg2=None):
        add_time("add_edge_hold_time", arg1, arg2)
        # done

    @validate_params
    @staticmethod
    def AddStrokeTime(arg0=None, arg1=None):
        handler = getattr(get_runtime()._current_frame, "handler", None)
        if not handler or not hasattr(handler, "add_time"):
            return
        if arg0 is None and arg1 is None:
            min = get_settings().taunt_cycle_min
            max = get_settings().taunt_cycle_max
            handler.add_time(random.randint(min, max) * 1000)
        elif isinstance(arg0, IntegerToken):
            min = arg0.Evaluate()
            if arg1 is None:
                handler.add_time(min * 1000)
            elif isinstance(arg1, IntegerToken):
                handler.add_time(random.randint(min, arg1.Evaluate()) * 1000)
            elif isinstance(arg1, StringToken):
                max = convert_string_time_to_seconds(arg1.Evaluate())
                handler.add_time(random.randint(min, max) * 1000)
        elif isinstance(arg0, StringToken):
            min = convert_string_time_to_seconds(arg0.Evaluate())
            if arg1 is None:
                handler.add_time(min * 1000)
            elif isinstance(arg1, IntegerToken):
                handler.add_time(random.randint(min, arg1.Evaluate()) * 1000)
            elif isinstance(arg1, StringToken):
                max = convert_string_time_to_seconds(arg1.Evaluate())
                handler.add_time(random.randint(min, max) * 1000)
        # done

    @validate_params
    @staticmethod
    def AddTeaseTime(arg1=None, arg2=None):
        add_time("add_tease_time", arg1, arg2)
        # Done

    @validate_params
    @staticmethod
    def Afternoon():
        hour = datetime.now().hour
        return hour > 12 and hour < 19
        # Done

    @validate_params
    @staticmethod
    def AllowsOrgasm():
        return get_settings().Domme.allows_orgasms != 5
        # Done

    @validate_params
    @staticmethod
    def ApathyLevel(arg0):
        return get_settings().Domme.apathy_level == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def BeforeTease():
        return get_runtime().round == 0
        # Done

    @validate_params
    @staticmethod
    def BookmarkLink():
        Bus.emit("bookmark_link")
        # Done

    @validate_params
    @staticmethod
    def BookmarkModule():
        Bus.emit("bookmark_module")
        # Done

    @validate_params
    @staticmethod
    def Call(arg0, arg1=None):
        get_runtime().call(arg0.Evaluate(), arg1.Evaluate() if arg1 is not None else None)
        # Done

    @validate_params
    @staticmethod
    def CallRandom(arg0):
        if os.path.isdir(arg0.Evaluate()):
            get_runtime().call(random_script(arg0.Evaluate()))
        else:
            ValueErr(
                "Invalid parameter: argument to @CallRandom must be a valid directory.", *arg0.get_position()
            ).throw()
        # Done

    @validate_params
    @staticmethod
    def CallReturn(arg0, arg1=None):
        get_runtime().call_return(arg0.Evaluate(), arg1.Evaluate() if arg1 is not None else None)
        # Done

    @validate_params
    @staticmethod
    def CameMode(arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @CameMode must be one of 'video' or 'goto'." * arg0.get_position()
            ).throw()
        CustomMode(get_runtime(), mode, arg1.Evaluate(), ["came"])
        # Done

    # BOOKMARK
    @validate_params
    @staticmethod
    def CBT(arg0=None):
        path = os.path.join(APPLICATION_ROOT, "SystemScripts")
        if arg0 is None:
            first = random.choice([f for f in os.listdir(path) if f.endswith("_First.txt")])
        else:
            val = arg0.Evaluate().lower()
            if val not in ["cock", "balls"]:
                ValueErr(
                    "Invalid parameter: argument to @CBT must be one of 'cock' or 'balls'", *arg0.get_position()
                ).throw()
            first = f"CBT{val.capitalize()}_First.txt"
            if val == "balls":
                get_runtime().cbt_balls += 1

        full_path_first = os.path.join(path, first)
        script_text = ""

        if os.path.isfile(full_path_first):
            with open(full_path_first, "r") as f:
                lines = f.readlines()
            if lines:
                script_text += random.choice(lines).strip() + "\n"
        else:
            RuntimeErr(f"Missing file for CBT task generation: {first}").throw()

        if arg0 is None:
            files = [file for file in os.listdir(path) if file.startswith("CBT") and not file.endswith("_First.txt")]
            file = random.choice(files) if files else None
        else:
            file = f"CBT{val.capitalize()}.txt"

        full_path_file = os.path.join(path, file) if file else None
        tasks = random.randint(1, 5) * get_settings().Sub.CBTLevel

        if full_path_file and os.path.isfile(full_path_file):
            with open(full_path_file, "r") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            while tasks > 0 and lines:
                script_text += random.choice(lines) + "\n"
                tasks -= 1
        else:
            RuntimeErr(f"Missing file for CBT task generation: {file}", *arg0.get_position()).throw()

        script_text += "\n@End\n"
        # Switch state to cbt or cbt_balls
        state_mode = "cbt_balls" if (arg0 and arg0.Evaluate().lower() == "balls") else "cbt_cock"
        get_runtime()._state = state_mode
        get_runtime().execute_memory_script(script_text, source_name="CBT_Routine", context="cbt")

    @validate_params
    @staticmethod
    def CBTLevel(arg0):
        return get_settings().Sub.CBTLevel == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def CensorbarOff(arg0, arg1=None):
        num = int(arg0.Evaluate())
        Bus.emit("hide_censor_bar", num)

    @validate_params
    @staticmethod
    def CensorbarOn(arg0, arg1, arg2, arg3, arg4, arg5=None):
        num = int(arg0.Evaluate())
        x = int(arg1.Evaluate())
        y = int(arg2.Evaluate())
        w = int(arg3.Evaluate())
        h = int(arg4.Evaluate())
        text = str(arg5.Evaluate()) if arg5 else ""
        Bus.emit("show_censor_bar", num, x, y, w, h, text)

    @validate_params
    @staticmethod
    def Chance(arg0, arg1):
        if random.randint(0, 100) < arg0.Evaluate():
            get_runtime().goto(arg1.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def Chastity(arg0):
        get_runtime().in_chastity = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def ChastityPA():
        return get_settings().Sub.chastity_piercing
        # Done

    @validate_params
    @staticmethod
    def ChastitySpikes():
        return get_settings().Sub.chastity_spikes
        # Done

    @validate_params
    @staticmethod
    def ChatImage(arg0):
        return f'<img src="{arg0.Evaluate()}">'
        # Done

    @validate_params
    @staticmethod
    def CheckBnB():
        boobs = get_settings().boobs_images
        butts = get_settings().butts_images
        if not os.path.isdir(boobs) or len(os.listdir(boobs)) == 0:
            boobs = False
        if not os.path.isdir(butts) or len(os.listdir(butts)) == 0:
            butts = False
        if not boobs and not butts:
            get_runtime().goto("No BnB")
        # Done

    @validate_params
    @staticmethod
    def CheckDate(arg0, arg1=None, arg2=None):
        varpath = os.path.join(APPLICATION_ROOT, "Scripts", get_settings().current_personality, "System\\Variables")
        if os.path.isfile(os.path.join(varpath, arg0.Evaluate())):
            with open(os.path.join(varpath, arg0.Evaluate()), "r") as f:
                date = date_from_string(f.read())
            if arg1 is None and date < datetime.now():
                return True
            if arg1:
                delta_seconds = convert_string_time_to_seconds(arg1.Evaluate())
                if delta_seconds == "invalid units":
                    ValueErr("Invalid time units", *arg1.get_position()).throw()
                if arg2 is None and date < datetime.now() - timedelta(seconds=delta_seconds):
                    return True
                elif arg2:
                    delta_seconds2 = convert_string_time_to_seconds(arg2.Evaluate())
                    if delta_seconds2 == "invalid units":
                        ValueErr("Invalid time units", *arg1.get_position()).throw()
                    if date < datetime.now() - timedelta(seconds=delta_seconds) and date > datetime.now() - timedelta(
                        seconds=delta_seconds2
                    ):
                        return True
        else:
            RuntimeErr(f"Variable {arg0.Evaluate()} not found", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def CheckFlag(arg0, arg1):
        flag = arg0.Evaluate()
        flags = getattr(get_settings(), "Flags", {}).setdefault(get_settings().current_personality, [])
        if flag in flags or flag in get_runtime()._temp_flags:
            get_runtime().goto(arg1.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def CheckJoiVideo():
        if not os.path.isdir(get_settings().joi_video) or len(os.listdir(get_settings().joi_video)) == 0:
            get_runtime().goto("No JOI Found")
        # Done

    @validate_params
    @staticmethod
    def CheckStrokingState():
        if get_runtime().state == "stroking":
            get_runtime().goto("Sub Stroking")
        # Done

    @validate_params
    @staticmethod
    def CheckTnA():
        if get_runtime().tna_result:
            get_runtime().goto(get_runtime().tna_result)
        # Done

    @validate_params
    @staticmethod
    def CheckVideo():
        video_dirs = [
            get_settings().joi_video,
            get_settings().hardcore_video,
            get_settings().softcore_video,
            get_settings().lesbian_video,
            get_settings().blowjob_video,
            get_settings().femdom_video,
            get_settings().femsub_video,
            get_settings().ch_video,
            get_settings().general_video,
        ]
        if all(os.path.isdir(video_dir) and len(os.listdir(video_dir)) > 0 for video_dir in video_dirs):
            return get_runtime().goto("Videos Found")
        return get_runtime().goto("No Videos Found")
        # Done

    @validate_params
    @staticmethod
    def ClearChat():
        Bus.emit("clear_chat")
        # NFI - hook up in chat window

    @validate_params
    @staticmethod
    def ClearModes():
        Bus.emit("clear_modes")
        # Done

    @validate_params
    @staticmethod
    def Contact(arg0):
        get_runtime().active_domme = get_settings().domme_id_to_object(arg0.Evaluate()).name
        # Done

    @validate_params
    @staticmethod
    def ContactKeyword(arg0, arg1):
        return get_settings().contact_namespace(arg0.Evaluate(), arg1.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def ContinueVideo():
        Bus.emit("unpause_video")
        # Done

    @validate_params
    @staticmethod
    def CountVar(arg0):
        var_name = arg0.Evaluate()
        if not is_valid_filename(var_name):
            ValueErr("Invalid filename specified for @CountVar", *arg0.get_position()).throw()

        def count():
            i = 0
            while True:
                vars_dict = getattr(get_settings(), "Variables", {}).setdefault(get_settings().current_personality, {})
                vars_dict[var_name] = i
                Bus.emit("save_settings")
                i += 1
                yield i

        from PySide6.QtCore import QTimer

        timer = QTimer(get_runtime()._current_frame.handler)
        timer.timeout.connect(lambda: next(count()))
        timer.start(1000)
        # Done

    @validate_params
    @staticmethod
    def CumForMe():
        return Dispatch.vocab("#CumForMe")
        # Done

    @validate_params
    @staticmethod
    def CustomMode(arg0, arg1, arg2):
        mode = arg1.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @CustomMode must be one of 'video' or 'goto'",
                *arg1.get_position(),
            ).throw()
        CustomMode(arg0.Evaluate(), mode, arg2)
        # Done

    @validate_params
    @staticmethod
    def CustomTask(arg0):
        filename = arg0.Evaluate()
        path = os.path.join(APPLICATION_ROOT, "Custon\\Tasks")
        first = os.path.join(path, filename + "_First.txt")
        if os.path.isfile(first):
            with open(first, "r") as f:
                lines = f.readlines()
            index = random.randint(0, len(lines) - 1)
            line = lines[index]
            index += 1
            get_runtime().execute_string(line, first, index)
        else:
            RuntimeErr(f"Missing file for custom task generation: {first}", *arg0.get_postion()).throw()
        file = os.path.join(path, filename + ".txt")
        tasks = random.randint(1, 5) * get_settings().Sub.ctb_level
        if os.path.isfile(file):
            with open(file, "r") as f:
                lines = f.readlines()
            while tasks > 0:
                index = random.randint(0, len(lines) - 1)
                line = lines[index]
                index += 1
                tasks -= 1
                get_runtime().execute_string(line, first, index)
        else:
            RuntimeErr(f"Missing file for custom task generation: {first}", *arg0.get_postion()).throw()
        # Done

    @validate_params
    @staticmethod
    def DateDifference(arg0, arg1):
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
    def Day(arg0):
        return arg0.Evaluate() == datetime.now().day
        # Done

    @validate_params
    @staticmethod
    def DayOfWeek(arg0):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[datetime.now().isoweekday()] == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def DecideEdge():
        if random.randint(0, 1) == 0:
            return Dispatch.vocab("#HoldTheEdge")
        else:
            return Dispatch.vocab("#StopStrokingEdge")
        # Done

    @validate_params
    @staticmethod
    def DecideOrgasm(arg0, arg1, arg2):
        chance_map = {1: 100, 2: 75, 3: 50, 4: 20, 5: 0}
        if get_runtime()._current_frame.context == "end":
            if random.randint(0, 100) < chance_map[get_settings().Domme.allows_orgasms]:
                get_runtime().goto(arg0.Evaluate() if arg0 is not None else "Orgasm Allow")
            else:
                if random.randint(0, 100) < chance_map[get_settings().Domme.ruins_orgasms]:
                    get_runtime().goto(arg1.Evaluate() if arg1 is not None else "Orgasm Ruin")
                else:
                    get_runtime().goto(arg2.Evaluate() if arg2 is not None else "Orgasm Deny")
        else:
            SyntaxErr("@DecideOrgasm is only allowed in end scripts", *get_runtime().get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def DecreaseOrgasmChance():
        get_settings().Domme.allows_orgasms -= 1
        # Done

    @validate_params
    @staticmethod
    def DecreaseRuinChance():
        get_settings().Domme.ruins_orgasms -= 1
        # Done

    @validate_params
    @staticmethod
    def DeleteFlag(arg0):
        flag = arg0.Evaluate()
        if flag in get_runtime()._temp_flags:
            get_runtime()._temp_flags.remove(flag)
        flags = getattr(get_settings(), "Flags", {}).setdefault(get_settings().current_personality, [])
        if flag in flags:
            flags.remove(flag)
            Bus.emit("save_settings")
        # Done

    @validate_params
    @staticmethod
    def DeleteLocalImage(arg0):
        if not get_settings().domme_delete:
            return
        if os.path.isfile(arg0.Evaluate()):
            response = {"current_image": None}
            Bus.emit("get_current_image", response=response)
            shutil.move(
                response["current_image"],
                os.path.join(APPLICATION_ROOT, "\\DeletedImages\\", os.path.basename(arg0.Evaluate())),
            )
        # Done

    @validate_params
    @staticmethod
    def DeleteVar(arg0):
        var_name = arg0.Evaluate()
        vars_dict = getattr(get_settings(), "Variables", {}).setdefault(get_settings().current_personality, {})
        if var_name in vars_dict:
            del vars_dict[var_name]
            Bus.emit("save_settings")
        # Done

    @validate_params
    @staticmethod
    def DifferentAnswer():
        pass  # doesn't need an implementation, we just match the string value
        # Done

    @validate_params
    @staticmethod
    def DislikeBlogImage():
        response = {"current_image": None}
        Bus.emit("get_current_image", response=response)
        if os.path.isfile(response["current_image"]):
            shutil.move(
                response["current_image"],
                os.path.join(APPLICATION_ROOT, "\\DislikedImages\\", os.path.basename(response["current_image"])),
            )
        # Done

    @validate_params
    @staticmethod
    def Domme(arg0):
        return get_settings().domme_namespace(arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def DommeAvatarReset():
        if get_settings().Domme.avatar_backup:
            get_settings().Domme._avatar = get_settings().Domme.avatar_backup
            get_settings().Domme.avatar_backup = None
        # Done

    @validate_params
    @staticmethod
    def DommeAvatarTemp(arg0):
        get_settings().Domme.avatar_backup = get_settings().Domme._avatar
        get_settings().Domme._avatar = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def DommeLevel(*args):
        for arg in args:
            if get_settings().Domme.Level == arg.Evaluate():
                return True
        return False
        # Done

    @validate_params
    @staticmethod
    def DommeNameReset():
        if get_settings().Domme.name_backup:
            get_settings().Domme.name = get_settings().Domme.name_backup
            get_settings().Domme.name_backup = None
        # Done

    @validate_params
    @staticmethod
    def DommeNameTemp(arg0):
        get_settings().Domme.name_backup = get_settings().Domme.name
        get_settings().Domme.name = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def DommeTag(*args):
        args = [arg.Evaluate() for arg in args]
        if os.path.isdir(get_settings().Domme._image_folder):
            if os.path.isfile(os.path.join(get_settings().Domme._image_folder, "ImageTags.txt")):
                with open(os.path.join(get_settings().Domme._image_folder, "ImageTags.txt"), "r") as f:
                    lines = f.readlines()
                lines = [line.split() for line in lines]
                response = {"current_image": None}
                Bus.emit("get_current_image", response)
                for line in lines:
                    if (
                        all(args) in line
                        and os.path.join(get_settings().Domme._image_folder, line[0]) == response["current_image"]
                    ):
                        return True
                return False
        # Done

    @validate_params
    @staticmethod
    def DommeTagAny(*args):
        args = [arg.Evaluate() for arg in args]
        if os.path.isdir(get_settings().Domme._image_folder):
            if os.path.isfile(os.path.join(get_settings().Domme._image_folder, "ImageTags.txt")):
                with open(os.path.join(get_settings().Domme._image_folder, "ImageTags.txt"), "r") as f:
                    lines = f.readlines()
                lines = [line.split() for line in lines]
                response = {"current_image": None}
                Bus.emit("get_current_image", response)
                for line in lines:
                    if (
                        any(args) in line
                        and os.path.join(get_settings().Domme._image_folder, line[0]) == response["current_image"]
                    ):
                        return True
                return False
        # Done

    @validate_params
    @staticmethod
    def Edge(*args):
        runtime = get_runtime()
        if runtime._state != "stroking":
            return RuntimeErr("@Edge can only be called when the sub is stroking", *runtime.get_position()).throw()
        get_settings()._edge_start = datetime.now()
        runtime._state = "edging"
        runtime.edges += 1

        hold = None
        resolution = None
        ruin_taunts = False

        if len(args) > 0:
            params = [arg.Evaluate().lower() for arg in args]
            params.append(None)
            hold = [param for param in ("extremehold", "longhold", "hold", None) if param in params][0]
            resolution = [param for param in ("ruin", "orgasm", None) if param in params][0]

            if "ruintaunts" in params and "ruin" not in params:
                return SyntaxErr(
                    "RuinTaunts is only valid when 'Ruin' is also passed as a paramter to @Edge",
                    *runtime.get_position(),
                ).throw()
            elif "ruintaunts" in params:
                ruin_taunts = True

        script_path = random_script(
            os.path.join(APPLICATION_ROOT, "Scripts", get_settings().current_personality, "Stroke\\Edge")
        )
        handler = EdgeTauntCycle(script_path, pending_hold=hold, pending_res=resolution, ruin_taunts=ruin_taunts)
        handler.start()

    @validate_params
    @staticmethod
    def EdgeHold(arg0=None):
        # If present, we map the parameter to user-configured min/max hold time settings and constrain it to those values.
        # To implement, we call the parameterized form of @Edge
        if arg0:
            duration = convert_string_time_to_seconds(arg0.Evaluate())
            if duration == "invalid units":
                ValueErr("Invalid parameter for @EdgeHold", *arg0.get_position()).throw()
            if duration < get_settings().Sub.max_edge_hold_time:
                Dispatch.Edge(StringToken(*arg0.get_position(), "Hold"))
            if duration > get_settings().Sub.max_edge_hold_time and duration < get_settings().Sub.min_extreme_hold_time:
                Dispatch.Edge(StringToken(*arg0.get_position(), "LongHold"))
            if duration > get_settings().Sub.max_extreme_hold_time:
                Dispatch.Edge(StringToken(*arg0.get_position(), "ExtremeHold"))
        else:
            Dispatch.Edge(StringToken(*get_runtime().get_position(), "Hold"))
        # Done

    @validate_params
    @staticmethod
    def EdgeHoldKeyword():
        return Dispatch.vocab("#EdgeHold")
        # Done

    @validate_params
    @staticmethod
    def EdgeMode(arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @EdgeMode must be one of 'video' or 'goto'", *arg0.get_position()
            )
        CustomMode(mode, arg1, "edge")

    @validate_params
    @staticmethod
    def Edging():
        return get_runtime()._state == "edging"
        # Done

    @validate_params
    @staticmethod
    def EmoteMessage():
        get_runtime().emote_message = True
        # Done

    # BOOKMARK
    @validate_params
    @staticmethod
    def End():
        runtime = get_runtime()
        personality_path = os.path.join(APPLICATION_ROOT, "Scripts", get_settings().current_personality)
        popped_frame = runtime._stack.pop()
        if len(runtime._stack) > 0:
            runtime._current_frame = runtime._stack[-1]
            return runtime.run()
        context = popped_frame.context

        if context == "taunt":
            return RuntimeErr("@End is not valid inside a taunt script", *runtime.get_position()).throw()
        elif context == "start":
            runtime.call(random_script(os.path.join(personality_path, "Stroke\\Link")))
        elif context == "link":
            if runtime._bookmark_module is not None:
                frame, pointer = runtime._bookmark_module
                runtime._bookmark_module = None
                frame.pointer = pointer
                runtime._stack.append(frame)
                runtime._current_frame = frame
                runtime.run()
            elif runtime._next_module is not None:
                runtime.call(runtime._next_module)
                runtime._next_module = None
            else:
                runtime.call(random_script(os.path.join(personality_path, "Modules")))
        elif context in ["module", "custom"]:
            if not runtime._finish_tease:
                runtime.call(random_script(os.path.join(personality_path, "Stroke\\End")))
            else:
                runtime.round += 1
                if runtime._bookmark_link is not None:
                    frame, pointer = runtime._bookmark_link
                    runtime._bookmark_link = None
                    frame.pointer = pointer
                    runtime._stack.append(frame)
                    runtime._current_frame = frame
                    runtime.run()
                elif runtime._next_link is not None:
                    runtime.call(runtime._next_link)
                    runtime._next_link = None
                else:
                    runtime.call(random_script(os.path.join(personality_path, "Stroke\\Link")))
        elif context == "end":
            Bus.emit("end_tease")
        # Done

    @validate_params
    @staticmethod
    def EndTease():
        Bus.emit("end_tease")
        # Done

    @validate_params
    @staticmethod
    def ExpireFlag(arg0, arg1):
        filename = arg0.Evaluate()
        if not is_valid_filename(filename):
            ValueErr("Invalid filename specified for @ExpireFlag", *arg0.get_position()).throw()
        time = convert_string_time_to_seconds(arg1.Evaluate())
        date = datetime.now() + timedelta(seconds=time)

        flags = getattr(get_settings(), "Flags", {}).setdefault(get_settings().current_personality, {})
        # ExpireFlag traditionally stores a date, we will store it as a dict key for backwards logical compat later,
        # but since flags is usually a list, we just append it for now as a simple flag:
        if isinstance(flags, list):
            if filename not in flags:
                flags.append(filename)
        elif isinstance(flags, dict):
            flags[filename] = string_from_date(date)

        Bus.emit("save_settings")
        # Done

    @validate_params
    @staticmethod
    def ExtremeHold():
        return Dispatch.vocab("#ExtremeHold")
        # Done

    @validate_params
    @staticmethod
    def ExtremeHoldKeyword():
        return Dispatch.vocab("#ExtremeHold")
        # NFI - Create this vocab file

    @validate_params
    @staticmethod
    def ExtremeTaunt():
        return get_runtime()._state == "extreme_hold"
        # Done

    @validate_params
    @staticmethod
    def FirstRound():
        return get_runtime().round == 1
        # Done

    @validate_params
    @staticmethod
    def Flag(arg0):
        flag = arg0.Evaluate()
        if flag in get_runtime()._temp_flags:
            return True
        flags = getattr(get_settings(), "Flags", {}).setdefault(get_settings().current_personality, [])
        return flag in flags
        # Done

    @validate_params
    @staticmethod
    def FlagOr(*args):
        return any([Dispatch.Flag(arg) for arg in args])
        # Done

    @validate_params
    @staticmethod
    def FollowUp(arg0, arg1):
        if random.randint(0, 100) < arg0.Evaluate():
            get_runtime().generic_visit(arg1)
        # Done

    @validate_params
    @staticmethod
    def GeneralTime():
        return Dispatch.vocab("#GeneralTime")
        # Done

    @validate_params
    @staticmethod
    def GoodAfternoonSub():
        return Dispatch.vocab("#GoodAfternoonSub")
        # Done

    @validate_params
    @staticmethod
    def GoodEveningSub():
        return Dispatch.vocab("#GoodEveningSub")
        # Done

    @validate_params
    @staticmethod
    def GoodMood():
        return get_runtime().domme_mood >= get_settings().Domme.mood_index_max
        # Done

    @validate_params
    @staticmethod
    def GoodMorningSub():
        return Dispatch.vocab("#GoodMorningSub")
        # Done

    @register("Goto")
    @validate_params
    @staticmethod
    def Goto(arg0):
        get_runtime().goto(arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def GotoDommeApathy():
        level = ""
        match get_settings().Domme.ApathyLevel:
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
        get_runtime().goto(level)

    # Done

    @validate_params
    @staticmethod
    def GotoDommeLevel():
        level = ""
        match get_settings().Domme.Level:
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
        get_runtime().goto(level)

    # Done

    @validate_params
    @staticmethod
    def GotoDommeOrgasm():
        get_runtime().goto(get_settings().Domme.allows_orgasms_string)

    # Done

    @validate_params
    @staticmethod
    def GotoDommeRuin():
        get_runtime().goto(get_settings().Domme.ruins_orgasms_string)

    # Done

    @validate_params
    @staticmethod
    def GreetSub():
        return Dispatch.vocab("#GreetSub")
        # Done

    @validate_params
    @staticmethod
    def Group(arg0):
        members = arg0.Evaluate().split("")
        return all([member in get_runtime()._present for member in members])
        # Done

    @validate_params
    @staticmethod
    def GroupContains(arg0):
        members = arg0.Evaluate().split("")
        return any([member in get_runtime()._present for member in members])
        # Done

    @validate_params
    @staticmethod
    def HentaiImageCount():
        if os.path.isdir(get_settings().hentai_images):
            return len(os.listdir(get_settings().hentai_images))
        return 0
        # Done

    @validate_params
    @staticmethod
    def HideChatMessage():
        get_runtime()._hide_chat = True
        # Done

    @validate_params
    @staticmethod
    def HoldTaunt():
        return get_runtime()._state == "holding"
        # Done

    @validate_params
    @staticmethod
    def HoldingTheEdge():
        return get_runtime()._state == "holding"
        # Done

    @validate_params
    @staticmethod
    def ImageBarOff(arg0, arg1=None):
        num = int(arg0.Evaluate())
        Bus.emit("hide_image_bar", num)

    @validate_params
    @staticmethod
    def ImageBarOn(arg0, arg1, arg2, arg3, arg4, arg5=None):
        num = int(arg0.Evaluate())
        x = int(arg1.Evaluate())
        y = int(arg2.Evaluate())
        w = int(arg3.Evaluate())
        h = int(arg4.Evaluate())
        path = str(arg5.Evaluate()) if arg5 else ""
        Bus.emit("show_image_bar", num, x, y, w, h, path)

    @validate_params
    @staticmethod
    def ImageTag(*args):
        Bus.emit("show_image_tag", [arg.Evaluate() for arg in args])
        # Done

    @validate_params
    @staticmethod
    def ImageTagAny(*args):
        Bus.emit("show_image_tag_any", [arg.Evaluate() for arg in args])
        # Done

    @validate_params
    @staticmethod
    def InChastity():
        return get_runtime().in_chastity
        # Done

    @validate_params
    @staticmethod
    def IncreaseOrgasmChance():
        get_settings().Domme.allows_orgasms += 1
        # NFI - Add settings change request popup?

    @validate_params
    @staticmethod
    def IncreaseRuinChance():
        get_settings().Domme.ruins_orgasms += 1
        # NFI - Add settings change request popup?

    @validate_params
    @staticmethod
    def InputVar(arg0):
        filename = arg0.Evaluate()
        if not is_valid_filename(filename):
            ValueErr("Invalid filename specified for @InputVar", *arg0.get_position()).throw()

        from message_classes import UserMessage

        def input_var_handler(message):
            if isinstance(message, UserMessage):
                vars_dict = getattr(get_settings(), "Variables", {}).setdefault(get_settings().current_personality, {})
                vars_dict[filename] = message.text
                Bus.emit("save_settings")
                Bus.unsub("new_message", input_var_handler)

        Bus.sub("new_message", input_var_handler)
        # Done

    @validate_params
    @staticmethod
    def Interrupt(arg0, arg1=None):
        if get_runtime()._interrupts_enabled:
            get_runtime()._worship_mode = False
            if os.path.isfile(
                os.path.join(
                    APPLICATION_ROOT,
                    "Scripts",
                    get_settings().current_personality,
                    "Interrupt",
                    arg0.Evaluate() + ".txt",
                )
            ):
                get_runtime().call_return(arg0.Evaluate(), arg1.Evaluate() if arg1 else None)
            else:
                RuntimeErr(
                    f"Script file {arg0.Evaluate()} not found for @Interrupt call", *get_runtime().get_position()
                ).throw()
        # Done

    @validate_params
    @staticmethod
    def InterruptLongEdge():
        runtime = get_runtime()
        if runtime._state != "edging":
            return
        settings = get_settings()
        if not settings.Sub.long_edge_interrupts:
            return
        if settings._edge_start is None:
            return
        delta = datetime.now() - settings._edge_start
        if delta.seconds > settings.Sub.long_edge_threshold:
            # The line itself handles chat output; we just terminate the cycle
            handler = runtime._current_frame.handler
            if handler is not None:
                handler.interrupt_long_edge()
        # Done

    @validate_params
    @staticmethod
    def Interrupts(arg0):
        get_runtime()._interrupts_enabled = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def LastJoined():
        return get_runtime().last_joined
        # Done

    @validate_params
    @staticmethod
    def LikeBlogImage():
        response = {"current_image": None}
        Bus.emit("get_current_image", response=response)
        if os.path.isfile(response["current_image"]):
            shutil.move(
                response["current_image"],
                os.path.join(APPLICATION_ROOT, "\\LikedImages\\", os.path.basename(response["current_image"])),
            )
        # Done

    @validate_params
    @staticmethod
    def LikedImageCount():
        path = os.path.join(APPLICATION_ROOT, "\\Liked Images\\")
        return sum([1 for _ in os.listdir(path)])
        # Done

    @validate_params
    @staticmethod
    def LockMedia():
        Bus.emit("lock_media")
        # Done

    @validate_params
    @staticmethod
    def LongEdge():
        if not get_settings().Sub.long_edge_interrupts:
            return False
        threshold = (
            get_settings().Sub.avg_edge_time
            if get_settings().Sub.use_avg_as_threshold
            else get_settings().Sub.long_edge_threshold * 60
        )
        if get_settings()._edge_start is not None:
            delta_time = datetime.now() - get_settings()._edge_start
            if delta_time.seconds > threshold:
                return True
        return False
        # Done

    @validate_params
    @staticmethod
    def LongHold():
        return Dispatch.vocab("#LongHold")
        # Done

    @validate_params
    @staticmethod
    def LongTaunt():
        return get_runtime()._current_frame.context == "long_hold"
        # Done

    @validate_params
    @staticmethod
    def LoopAnswer():
        pass  # This command is implemented as a no-op because the interpreter is already in waiting_for_input
        # state.   No state change is needed for the state to persist.  The intent of this command is simply
        # to notify the interpreter *not* to resolve the MultipleChoiceBlock
        # Done

    @validate_params
    @staticmethod
    def Month(arg0):
        return arg0.Evaluate() == datetime.now().month
        # Done

    @validate_params
    @staticmethod
    def Mood(arg0):
        return get_runtime().domme_mood == arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def Morning():
        return datetime.now().hour > 6 and datetime.now().hour < 12
        # Done

    @validate_params
    @staticmethod
    def MultipleEdges(arg0, arg1, arg2):
        if arg2 is not None:
            if random.randint(0, 100) > arg2.Evaluate():
                return
        runtime = get_runtime()
        if runtime._state != "edging":
            return RuntimeErr("@MultipleEdges is only valid when preceded by @Edge", *arg0.get_position()).throw()
        runtime._current_frame.multiple_edges = arg0.Evaluate()
        if arg1 is not None:
            runtime._current_frame.multiple_edges_interval = arg1.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def NewContactSlideshow(arg0):
        dir = get_settings().contact_namespace(arg0.Evaluate(), "_image_folder")
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
    def NewDommeSlideshow():
        dir = get_settings().Domme._image_folder
        if os.path.isdir(dir):
            folders = [f for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]
            if len(folders) > 0:
                folder = folders[random.randint(0, len(folders) - 1)]
                Bus.emit("new_slideshow", folder)
        else:
            ValueErr("Invalid directory passed to @NewDommeSlideshow", 0, 0, "").throw()
        # Done

    @validate_params
    @staticmethod
    def Night():
        return datetime.now().hour > 19 or datetime.now().hour < 6
        # Done

    @validate_params
    @staticmethod
    def NoMode(arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @NoMode must be one of 'video' or 'goto'", *arg0.get_position()
            )
        CustomMode(mode, arg1, "no")
        # Done

    @validate_params
    @staticmethod
    def Null():
        return ""
        # Done

    @validate_params
    @staticmethod
    def NullNextDommeImage():
        get_runtime()._null_domme_image = True
        # Done

    @validate_params
    @staticmethod
    def OrgasmAllow():
        runtime = get_runtime()
        if not runtime.orgasm_restricted:
            runtime.orgasm_allowed = True
            runtime.settings().Sub.last_orgasm_date = string_from_date(datetime.now())
            runtime.goto("Orgasm Allow")
        else:
            RuntimeErr(
                "@OrgasmAllow cannot be called while @OrgasmRestricted is in effect.", *runtime.get_position()
            ).throw()
        # Done

    @validate_params
    @staticmethod
    def OrgasmAllowed():
        return get_runtime().orgasm_allowed
        # Done

    @validate_params
    @staticmethod
    def OrgasmDenied():
        return get_runtime().orgasm_denied
        # Done

    @validate_params
    @staticmethod
    def OrgasmDeny():
        get_runtime().orgasm_denied = True
        get_runtime().goto("Orgasm Deny")
        # Done

    @validate_params
    @staticmethod
    def OrgasmLockDate():
        return get_settings().orgasm_lock_date
        # Done

    @validate_params
    @staticmethod
    def OrgasmRestricted():
        return get_runtime().orgasm_restricted
        # Done

    @validate_params
    @staticmethod
    def OrgasmRuin():
        runtime = get_runtime()
        runtime.orgasm_ruined = True
        runtime.settings.Sub.last_ruin_date = string_from_date(datetime.now())
        runtime.goto("Orgasm Ruin")
        # Done

    @validate_params
    @staticmethod
    def OrgasmRuined():
        return get_runtime().orgasm_ruined
        # Done

    @validate_params
    @staticmethod
    def PaceFastest():
        pace = {}
        Bus.emit("get_metro_pace", pace)
        return pace["pace"] == 120
        # Done

    @validate_params
    @staticmethod
    def PaceSlowest():
        pace = {}
        Bus.emit("get_metro_pace", pace)
        return pace["pace"] == 30
        # Done

    @validate_params
    @staticmethod
    def PauseVideo():
        Bus.emit("pause_video")
        # Done

    @validate_params
    @staticmethod
    def PetName():
        runtime = get_runtime()
        if getattr(runtime, "_petname_temp", None) is not None:
            return runtime._petname_temp
        names = []
        mood = runtime.domme_mood
        if mood <= get_settings().Domme.mood_index_min:
            names = get_settings().Domme._bad_mood_pet_names
        if mood > get_settings().Domme.mood_index_min and mood < get_settings().Domme.mood_index_max:
            names = get_settings().Domme._neutral_mood_pet_names
        if mood >= get_settings().Domme.mood_index_max:
            names = get_settings().Domme._good_mood_pet_names
        return random.choice(names)
        # Done

    @validate_params
    @staticmethod
    def PetNameReset():
        get_runtime()._petname_temp = None
        # Done

    @validate_params
    @staticmethod
    def PetNameTemp(arg0):
        get_runtime()._petname_temp = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def PlayAudio(arg0):
        Bus.emit("play_audio", arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def PlayAudioLoop(arg0, arg1):
        Bus.emit("play_audio_loop", arg0.Evaluate(), arg1.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def PlayAvoidTheEdge():
        runtime = get_runtime()
        Dispatch.CallReturn(
            StringToken(
                *runtime.get_position(), os.path.join(runtime.game_path, "\\Avoid The Edge\\Avoid The Edge.txt")
            )
        )
        # Done

    @validate_params
    @staticmethod
    def PlayCensorshipSucks():
        runtime = get_runtime()
        Dispatch.CallReturn(
            StringToken(
                *runtime.get_position(), os.path.join(runtime.game_path, "\\Censorship Sucks\\Censorship Sucks.txt")
            )
        )
        # Done

    @validate_params
    @staticmethod
    def PlayDommeGenreVideo(arg0):
        genre = arg0.Evaluate()
        dir = get_settings().domme_namespace(genre + "_video")
        video = random_video(dir)
        Dispatch._registry["PlayVideo"](StringToken(*arg0.get_position(), video))
        # Done

    @validate_params
    @staticmethod
    def PlayGenreVideo(arg0):
        genre = arg0.Evaluate()
        dir = getattr(get_settings(), genre + "_video")
        video = random_video(dir)
        Dispatch._registry["PlayVideo"](StringToken(*arg0.get_position(), video))
        # Done

    @validate_params
    @staticmethod
    def PlayRedLightGreenLight():
        runtime = get_runtime()
        Dispatch.CallReturn(
            StringToken(
                *runtime.get_position(),
                os.path.join(runtime.game_path, "\\Red Light Green Light\\Red Light Green Light.txt"),
            )
        )
        # Done

    @validate_params
    @staticmethod
    def PlayRiskyPick():
        runtime = get_runtime()
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
    def PlayVideo(arg0=None, arg1=None):
        if arg0 is None:
            files = []
            folders = [
                get_settings().blowjob_video,
                get_settings().ch_video,
                get_settings().joi_video,
                get_settings().hardcore_video,
                get_settings().softcore_video,
                get_settings().lesbian_video,
                get_settings().femdom_video,
                get_settings().femsub_video,
                get_settings().general_video,
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
    def RT(*args):
        return random.choice(args).Evaluate()
        # Done

    @validate_params
    @staticmethod
    def Random(arg0, arg1, arg2=None):
        num = random.randint(arg0.Evaluate(), arg1.Evaluate())
        if arg2 is not None:
            return round(num / arg2.Evaluate()) * arg2.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def RandomContact():
        runtime = get_runtime()
        contact = random.choice(runtime._present)
        runtime.active_domme = get_settings().contact_namespace(contact, "name")
        # Done

    @validate_params
    @staticmethod
    def RapidText(arg0):
        get_runtime().rapid_text = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def RarelyAllowsOrgasm():
        return get_settings().Domme.allows_orgasms == 4
        # Done

    @validate_params
    @staticmethod
    def RarelyRuinsOrgasm():
        return get_settings().Domme.ruins_orgasms == 4
        # Done

    @validate_params
    @staticmethod
    def RemoveContact(arg0):
        Bus.emit("remove_entity", arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def RemoveDomme():
        Bus.emit("remove_entity", "D")
        # Done

    @validate_params
    @staticmethod
    def RemoveEdgeHoldTime(arg0=None, arg1=None):
        runtime = get_runtime()
        handler = runtime._current_frame.handler
        if arg0 is None and arg1 is None:
            min = get_settings().Sub.min_edge_hold_time
            max = get_settings().Sub.max_edge_hold_time
            handler.hold_timer.setInterval(handler.hold_timer.remainingTime() - random.randint(min, max) * 1000)
        if isinstance(arg0, IntegerToken):
            min = arg0.Evaluate()
            if arg1 is None:
                handler.hold_timer.setInterval(handler.hold_timer.remainingTime() - min * 1000)
            elif isinstance(arg1, IntegerToken):
                handler.hold_timer.setInterval(
                    handler.hold_timer.remainingTime() - random.randint(min, arg1.Evaluate()) * 1000
                )
            else:
                max = convert_string_time_to_seconds(arg1.Evaluate())
                if max == "invalid units":
                    ValueErr(
                        f"Got invalid parameter {arg1.Evaluate()} for @RemoveEdgeHoldTime", *arg1.get_position()
                    ).throw()
                handler.hold_timer.setInterval(handler.hold_timer.remainingTime() - random.randint(min, max) * 1000)
        if isinstance(arg0, StringToken):
            min = convert_string_time_to_seconds(arg0.Evaluate())
            if min == "invalid units":
                ValueErr(
                    f"Got invalid parameter {arg0.Evaluate()} for @RemoveEdgeHoldTime", *arg0.get_position()
                ).throw()
            if arg1 is None:
                handler.hold_timer.setInterval(handler.hold_timer.remainingTime() - min * 1000)
            elif isinstance(arg1, IntegerToken):
                handler.hold_timer.setInterval(
                    handler.hold_timer.remainingTime() - random.randint(min, arg1.Evaluate()) * 1000
                )
            elif isinstance(arg1, StringToken):
                max = convert_string_time_to_seconds(arg1.Evaluate())
                if max == "invalid units":
                    ValueErr(f"Got invalid parameter {arg1.Evaluate()}", *arg0.get_position()).throw()
                handler.hold_timer.setInterval(handler.hold_timer.remainingTime() - random.randint(min, max) * 1000)
        if handler.hold_timer.remainingTime() <= 0:
            Bus.emit("stop_hold")
        # Done

    @validate_params
    @staticmethod
    def RemoveStrokeTime(arg0, arg1):
        handler = getattr(get_runtime()._current_frame, "handler", None)
        if not handler or not hasattr(handler, "remove_time"):
            return
        if arg0 is None and arg1 is None:
            min = get_settings().taunt_cycle_min
            max = get_settings().taunt_cycle_max
            handler.remove_time(random.randint(min, max) * 1000)
        elif isinstance(arg0, IntegerToken):
            min_val = arg0.Evaluate()
            if arg1 is None:
                handler.remove_time(min_val * 1000)
            elif isinstance(arg1, IntegerToken):
                handler.remove_time(random.randint(min_val, arg1.Evaluate()) * 1000)
            else:
                max_val = convert_string_time_to_seconds(arg1.Evaluate())
                handler.remove_time(random.randint(min_val, max_val) * 1000)
        elif isinstance(arg0, StringToken):
            min_val = convert_string_time_to_seconds(arg0.Evaluate())
            if arg1 is None:
                handler.remove_time(min_val * 1000)
            elif isinstance(arg1, IntegerToken):
                handler.remove_time(random.randint(min_val, arg1.Evaluate()) * 1000)
            elif isinstance(arg1, StringToken):
                max_val = convert_string_time_to_seconds(arg1.Evaluate())
                handler.remove_time(random.randint(min_val, max_val) * 1000)

        if hasattr(handler, "_cycle_timer") and handler._cycle_timer.remainingTime() <= 0:
            handler.on_cycle_end()
        # Done

    @validate_params
    @staticmethod
    def RemoveTeaseTime(arg0=None, arg1=None):
        runtime = get_runtime()
        if arg0 is None:
            min = get_settings().min_tease_length
            runtime.tease_time -= random.randint(min, runtime.tease_time)
        else:
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
            Bus.emit("finish_tease")
        # Done

    @validate_params
    @staticmethod
    def ResponseNo(arg0):
        runtime = get_runtime()
        if os.path.isfile(arg0.Evaluate()):
            runtime._response_no = True
            runtime._response_script = arg0.Evaluate()
        else:
            RuntimeErr(f"Script: {arg0.Evaluate()} not found", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def ResponseYes(arg0):
        runtime = get_runtime()
        if os.path.isfile(arg0.Evaluate()):
            runtime._response_yes = True
            runtime._response_script = arg0.Evaluate()
        else:
            RuntimeErr(f"Script: {arg0.Evaluate()} not found", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def RestrictOrgasm(arg0, arg1):
        get_runtime().orgasm_restricted = True
        # Done

    @validate_params
    @staticmethod
    def RuinTaunt():
        if get_runtime()._current_frame.context != "edging":
            return False
        return get_runtime()._current_frame.handler.ruin_taunts_enabled

    @validate_params
    @staticmethod
    def RuinYourOrgasm():
        return Dispatch.vocab("#RuinYourOrgasm")
        # Done

    @validate_params
    @staticmethod
    def RuinedMode(arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @RuinedMode must be one of 'video' or 'goto'",
                *arg0.get_position(),
            )
        CustomMode(mode, arg1, "ruined")
        # Done

    @validate_params
    @staticmethod
    def RuinsOrgasm():
        return get_settings().Domme.ruins_orgasms != 5
        # Done

    @validate_params
    @staticmethod
    def SYS_MultipleEdgesStart():
        return Dispatch.vocab("#SYS_MultipleEdgesStart")
        # Done

    @validate_params
    @staticmethod
    def Sadistic():
        return get_settings().Domme.sadistic
        # Done

    @validate_params
    @staticmethod
    def SelfOld():
        return get_settings().Domme.age > 50
        # Done

    @validate_params
    @staticmethod
    def SelfYoung():
        return get_settings().Domme.age < 30
        # Done

    @validate_params
    @staticmethod
    def SendDailyTasks():
        pass

    @validate_params
    @staticmethod
    def Session(arg0):
        return getattr(get_runtime(), arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def SessionCBTBalls():
        return get_runtime().cbt_balls
        # Done

    @validate_params
    @staticmethod
    def SessionEdges():
        return get_runtime().edges
        # Done

    @validate_params
    @staticmethod
    def SetDate(arg0, arg1):
        runtime = get_runtime()
        var_file = os.path.join(runtime.var_path, arg0.Evaluate())
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
    def SetDomme(arg0):
        runtime = get_runtime()
        if arg0.Evaluate() == "D":
            runtime.active_domme = get_settings().Domme.name
        elif arg0.Evaluate() >= 1 and arg0.Evaluate() <= 6:
            runtime.active_domme = get_settings().contact_namespace(arg0.Evaluate(), "name")
        else:
            ValueErr("Got invalid parameter for @SetDomme", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def SetFlag(arg0):
        flag = arg0.Evaluate()
        if not is_valid_filename(flag):
            ValueErr("Invalid filename specified for @SetFlag", *arg0.get_position()).throw()
        flags = getattr(get_settings(), "Flags", {}).setdefault(get_settings().current_personality, [])
        if flag not in flags:
            flags.append(flag)
            Bus.emit("save_settings")
        # Done

    @validate_params
    @staticmethod
    def SetImageBarImage(arg0, arg1=None):
        num = int(arg0.Evaluate())
        path = str(arg1.Evaluate()) if arg1 else ""
        Bus.emit("set_image_bar_image", num, path)

    @validate_params
    @staticmethod
    def SetLink(arg0):
        runtime = get_runtime()
        filepath = os.path.join(
            APPLICATION_ROOT, "Scripts", runtime.settings.current_personality, "Stroke", "Link", arg0.Evaluate()
        )
        if os.path.isfile(filepath):
            runtime._next_link = filepath
            return
        # NFI I'd really like to find a cleaner way to implement this, ideally re-using as much of BookmarkLink as possible

    @validate_params
    @staticmethod
    def SetModule(arg0, arg1=None):
        runtime = get_runtime()
        filepath = os.path.join(
            APPLICATION_ROOT, "Scripts", runtime.settings.current_personality, "Modules", arg0.Evaluate()
        )
        if os.path.isfile(filepath):
            runtime._next_module = filepath
            return
        # NFI See comment on SetLink

    @validate_params
    @staticmethod
    def SetMood(arg0):
        get_runtime().domme_mood = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def Settings(arg0):
        return getattr(get_settings(), arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def ShortName():
        return get_settings().Domme.short_name
        # Done

    @validate_params
    @staticmethod
    def ShowBlogImage():
        path = os.path.join(APPLICATION_ROOT, "url files")
        file = URL_File.from_json(random.choice(os.listdir(path)))
        file.load()
        Bus.emit("next_slide")
        # Done?

    @validate_params
    @staticmethod
    def ShowDislikedImage():
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
    def ShowImage(arg0):
        if is_image_file(arg0.Evaluate()):
            Bus.emit("show_image", arg0.Evaluate())
        else:
            TypeErr(f"{arg0.Evaluate()} is not a valid image file", *arg0.get_position()).throw()
        # Done

    @validate_params
    @staticmethod
    def ShowLikedImage():
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
    def ShowNotTaggedImage():
        dir = get_runtime()._slides_dir
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
    def ShowTaggedImage():
        dir = get_runtime()._slides_dir
        tag_imgs = []
        if os.path.isfile(os.path.join(dir, "ImageTags.txt")):
            with open(os.path.join(dir, "ImageTags.txt"), "r") as f:
                lines = f.readlines()
            for line in lines:
                tags = line.split()
                if len(tags) > 1:
                    tag_imgs.append(tags[0])
            Bus.emit("show_image", random.choice(tag_imgs))
        # Done

    @validate_params
    @staticmethod
    def ShowWait():
        get_runtime()._show_wait = True

    @validate_params
    @staticmethod
    def Slideshow(arg0, arg1=None, arg2=None):
        paths = []
        if path1 := getattr(get_settings(), f"{arg0.Evaluate().lower()}_images"):
            paths.append(path1)
            if arg1 is not None:
                if path2 := getattr(get_settings(), f"{arg1.Evaluate().lower()}_images"):
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
    def SlideshowOff():
        Bus.emit("stop_slideshow")
        # Done

    @validate_params
    @staticmethod
    def SlideshowOn():
        Bus.emit("start_slideshow")
        # Done

    @validate_params
    @staticmethod
    def SlideshowPause():
        Bus.emit("pause_slideshow")
        # Done

    @validate_params
    @staticmethod
    def SlowMotion(arg0):
        Bus.emit("start_slowmo")
        # Done

    @validate_params
    @staticmethod
    def SometimesAllowsOrgasm():
        return get_settings().Domme.allows_orgasms == 3
        # Done

    @validate_params
    @staticmethod
    def SometimesRuinsOrgasm():
        return get_settings().Domme.ruins_orgasms == 3
        # Done

    @validate_params
    @staticmethod
    def StartStroking():
        from execution_modes import StrokeTauntCycle, ChastityTauntCycle

        runtime = get_runtime()
        if runtime._state != "chatting":
            return RuntimeErr("@StartStroking is only valid when state is 'chatting'", *runtime.get_position()).throw()
        if get_settings().Sub.has_chastity and runtime.in_chastity:
            ChastityTauntCycle()
        else:
            StrokeTauntCycle()
        # Done

    @validate_params
    @staticmethod
    def StartStrokingKeyword():
        return Dispatch.vocab("#StartStroking")
        # Done

    @validate_params
    @staticmethod
    def StopStroking():
        runtime = get_runtime()
        runtime._worship_mode = False
        if runtime._state in ("stroking", "chastity_stroking"):
            handler = runtime._current_frame.handler
            if handler is not None:
                handler.on_cycle_end()
        # Done

    @validate_params
    @staticmethod
    def StopStrokingKeyword():
        return Dispatch.vocab("#StopStroking")
        # Done

    @validate_params
    @staticmethod
    def StopStrokingEdge():
        get_runtime()._worship_mode = False
        return Dispatch.vocab("#StopStrokingEdge")
        # NFI - Add this vocab file

    @validate_params
    @staticmethod
    def StopTnA():
        response_dict = {}
        Bus.emit("get_current_slide_path", response_dict)
        if os.path.dirname(response_dict["path"]) == get_settings().boobs_images:
            get_runtime()._tna_result = "boobs"
        elif os.path.dirname(response_dict["path"]) == get_settings().butts_images:
            get_runtime()._tna_result = "butts"
        Bus.emit("stop_slideshow")
        # Done?

    @validate_params
    @staticmethod
    def StopVideo():
        Bus.emit("stop_video")
        # Done

    @validate_params
    @staticmethod
    def StrokeCycleTime():
        handler = getattr(get_runtime()._current_frame, "handler", None)
        if handler and hasattr(handler, "get_time"):
            return handler.get_time()
        return 0

    @validate_params
    @staticmethod
    def StrokeFaster():
        runtime = get_runtime()
        if getattr(runtime, "_worship_mode", False):
            runtime._abort_line = True
            return
        Bus.emit("stroke_faster")
        # done

    @validate_params
    @staticmethod
    def StrokeFastest():
        runtime = get_runtime()
        if getattr(runtime, "_worship_mode", False):
            runtime._abort_line = True
            return
        Bus.emit("stroke_fastest")
        # Done

    @validate_params
    @staticmethod
    def StrokeSlower():
        Bus.emit("stroke_slower")
        # Done

    @validate_params
    @staticmethod
    def StrokeSlowest():
        Bus.emit("stroke_slowest")
        # Done

    @validate_params
    @staticmethod
    def Stroking():
        return get_runtime()._state in ("stroking", "chastity_stroking")
        # Done

    @validate_params
    @staticmethod
    def SubNameReset():
        get_runtime()._subname_temp = None
        # Done

    @validate_params
    @staticmethod
    def SubNameTemp(arg0):
        get_runtime()._subname_temp = arg0.Evaluate()
        # Done

    @validate_params
    @staticmethod
    def SubName():
        runtime = get_runtime()
        if runtime.subname_temp is not None:
            return runtime.subname_temp
        return get_settings().Sub.name
        # Done

    @validate_params
    @staticmethod
    def SubOld():
        return get_settings().Sub.age > 50
        # Done

    @validate_params
    @staticmethod
    def SubWritingTaskMax():
        return get_settings().writing_task_lines_max
        # Done

    @validate_params
    @staticmethod
    def SubWritingTaskMin():
        return get_settings().writing_task_lines_min
        # Done

    @validate_params
    @staticmethod
    def SubYoung():
        return get_settings().Sub.age < 30
        # Done

    @validate_params
    @staticmethod
    def Supremacist():
        return get_settings().Domme.supremacist
        # Done

    @validate_params
    @staticmethod
    def SystemMessage():
        get_runtime()._system_message = True
        # Done

    @validate_params
    @staticmethod
    def Tag(*args):
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
    def TagAny(*args):
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
    def TagGarment():
        tags = []
        Bus.emit("img_tags_requested", tags)
        for tag in tags:
            if tag.startswith("TagGarment"):
                return tag[9:]
        # Done

    @validate_params
    @staticmethod
    def TempFlag(arg0):
        get_runtime()._temp_flags.add(arg0.Evaluate())
        # Done

    @validate_params
    @staticmethod
    def Timeout(arg0, arg1):
        timer = QTimer.singleShot(arg0.Evaluate() * 1000, lambda: get_runtime().goto(arg1.Evaluate()))

        def cancel_timer(message):
            if isinstance(message, UserMessage):
                timer.stop()
                Bus.unsub("new_message", cancel_timer)

        Bus.sub("new_message", cancel_timer)
        # Done

    @validate_params
    @staticmethod
    def TnAFastSlides():
        folders = [folder for folder in (get_settings().boobs_images, get_settings().butts_images) if os.isdir(folder)]
        Bus.emit("new_slideshow", folders)
        Bus.emit("next_slide")

    @validate_params
    @staticmethod
    def TnAFastSlidesResult():
        return get_runtime().tna_result
        # Done

    @validate_params
    @staticmethod
    def UnlockMedia():
        get_runtime()._media_locked = False
        # Done

    @validate_params
    @staticmethod
    def ValentinesDay():
        return datetime.now().month == 2 and datetime.now().day == 14
        # Done

    @validate_params
    @staticmethod
    def Var(arg0):
        pass  # NOTE: This method never gets called, because visiting a VarRef calls Evaluate()
        # Done

    @validate_params
    @staticmethod
    def VarExists(arg0):
        var_name = arg0.Evaluate()
        vars_dict = getattr(get_settings(), "Variables", {}).setdefault(get_settings().current_personality, {})
        return var_name in vars_dict
        # Done

    @validate_params
    @staticmethod
    def VideoIsPaused():
        Bus.emit("get_video_info", info := {})
        return info["state"] == "pause"
        # Done

    @validate_params
    @staticmethod
    def VideoIsPlaying():
        Bus.emit("get_video_info", info := {})
        return info["state"] == "play"
        # Done

    @validate_params
    @staticmethod
    def VideoIsSlowMotion():
        Bus.emit("get_slowmo_state", info := {"slowmo": None})
        return info["slowmo"]
        # Done

    @validate_params
    @staticmethod
    def VideoLength():
        Bus.emit("get_video_info", info := {})
        return info["duration"]
        # Done

    @validate_params
    @staticmethod
    def VideoRemaining():
        Bus.emit("get_video_info", info := {})
        return info["duration"] - info["position"]
        # Done

    @validate_params
    @staticmethod
    def Vulgar():
        return get_settings().Domme.vulgar
        # Done

    @validate_params
    @staticmethod
    def Wait(arg0):
        duration = arg0.Evaluate()
        if get_runtime()._show_wait:
            Bus.emit("show_wait_ui", duration)
            get_runtime()._show_wait = False
        QTimer.singleShot(duration * 1000, lambda: Bus.emit("interpreter_ready"))
        # Done

    @validate_params
    @staticmethod
    def WaitAudio():
        info = {"remaining": None}
        Bus.emit("wait_audio", info)
        if info["remaining"] is not None:
            QTimer.singleShot(info["remaining"] * 1000, lambda: Bus.emit("interpreter_ready"))
        # Done

    @validate_params
    @staticmethod
    def WhoIsTyping(arg0):
        return get_settings().id_to_name(arg0.Evaluate()) == get_runtime().active_domme.name
        # Done

    @validate_params
    @staticmethod
    def Worship(arg0):
        if arg0.Evaluate().lower() in ["ass", "boobs", "feet", "pussy"]:
            get_runtime()._worship_mode_target = arg0.Evaluate().lower()
        else:
            RuntimeErr("Invalid target specified for Worship Mode", *arg0.get_position()).throw()

        get_runtime()._worship_mode = True
        Bus.emit("stroke_slowest")
        # Done

    @validate_params
    @staticmethod
    def WorshipOff():
        get_runtime()._worship_mode = False
        # Done

    @validate_params
    @staticmethod
    def WorshipOn():
        get_runtime()._worship_mode_target = None
        get_runtime()._worship_mode = True
        Bus.emit("stroke_slowest")
        # Done

    @validate_params
    @staticmethod
    def YesMode(arg0, arg1):
        mode = arg0.Evaluate().lower()
        if mode not in ["video", "goto"]:
            ValueErr(
                "Invalid parameter: first argument to @YesMode must be one of 'video' or 'goto'", *arg0.get_position()
            )
        CustomMode(mode, arg1, "yes")
        # Done
