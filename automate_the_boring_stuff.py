import json
import re

with open("command_registry.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for k, v in data["commands"].items():
    if v["category"] == "Command":
        v["return_value"] = ""
    elif v["category"] == "Command Filter":
        v["return_value"] = "bool"
    elif v["category"] == "Keyword":
        v["return_value"] = "string"


def _link_deprecated_by(text: str) -> str:
    def repl(match):
        cmd = match.group(1)
        anchor = cmd.lower().replace("@", "").replace("#", "")
        return f'<a href="#{anchor}" title="Jump to {cmd}" style="color: #7af;">{cmd}</a><span>'

    hidden_tags = []

    def hide(match):
        hidden_tags.append(match.group(0))
        return f"__HIDDEN_A_{len(hidden_tags) - 1}__"

    text = re.sub(r"<a\b[^>]*>.*?</a>", hide, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"([@#][a-zA-Z0-9]+)", repl, text, flags=re.IGNORECASE)
    for i, tag in enumerate(hidden_tags):
        text = text.replace(f"__HIDDEN_A_{i}__", tag)
    return text


def _link_commands(text: str) -> str:
    def repl(match):
        cmd = match.group(1)
        if cmd.startswith("@Chance") and len(cmd) > 7:
            return cmd
        if cmd.startswith("#RandomRound") and len(cmd) > 12:
            return cmd
        if cmd.startswith("@FollowUp") and len(cmd) > len("@FollowUp"):
            return cmd
        anchor = cmd.lower().replace("@", "").replace("#", "")
        return (
            f'<a href="#{anchor}" title="Jump to {cmd}" style="color: #7af;">{cmd}</a>'
        )

    hidden_tags = []

    def hide(match):
        hidden_tags.append(match.group(0))
        return f"__HIDDEN_A_{len(hidden_tags) - 1}__"

    text = re.sub(r"<a\b[^>]*>.*?</a>", hide, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"([@#]\w+)", repl, text, flags=re.IGNORECASE)
    for i, tag in enumerate(hidden_tags):
        text = text.replace(f"__HIDDEN_A_{i}__", tag)
    return text


def get_html(name, docstring, deprecated, syntax, params):
    params_by_pos = [[]]
    for param in params:
        while len(params_by_pos) - 1 < param.position:
            params_by_pos.append([])
        params_by_pos[param.position].append(param)

    html = f"""<div class="entry" id="{name.lstrip("@").lstrip("#").lower()}_entry">"""
    # Command Name
    html += (
        f"""<span id="{name.lstrip("@").lstrip("#").lower()}" class="cname">{name}"""
    )

    # Parameter signature
    if len(params) > 0:
        html += """</span><span class="parens">(</span>"""
    param_str = ""
    for i, param_pos in enumerate(params_by_pos):
        if len(param_pos) == 1:
            param_str += f"""<span class="param_name" title="{param_pos[0].description}">{param_pos[0].type}</span>"""
        # now handle multiple params in same pos
        else:
            for j, param in enumerate(param_pos):
                param_str += f'<span class="param_name" title="{param.description}">{param.type}</span>'
                param_str += (
                    '<span class="param_desc"> or </span>'
                    if j < len(params_by_pos) - 1
                    else ""
                )
        param_str += ", " if i < len(params_by_pos) - 1 else ""
    html += param_str
    if len(params) > 0:
        html += '<span class="parens">)'
        html += "<br>"
    html += "</span>"
    # Params list
    for param_pos in params_by_pos:
        for i, param in enumerate(param_pos):
            if i == 0:
                html += f"""<span class="list_param_pos">Position: {param.position + 1} </span>"""
            else:
                html += """<span class="list_param_pos">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"""
            html += f"""<span class="list_param_name">{param.type}</span> """
            if param.optional:
                html += """ <span class="param_parens">(</span><span class="param_desc">optional</span><span class="param_parens">)</span> """
            html += f"""<span class="param_desc"> - {param.description}</span>{"<br>" if params.index(param) < len(params) - 1 else ""}"""

    # Syntax Examples
    html += f"""<br><code class="syntax">{syntax}</code>"""

    # Docstring
    html += f"""<p class="docs">{_link_commands(docstring)}</p>"""

    # Deprecated by
    if deprecated not in [None, "", "None"]:
        html += f"""<span class="deprecated">&nbsp;Deprecated by: {_link_deprecated_by(deprecated)}</span>"""
    html += """</div>"""

    return html


toy_keywords = [
    "#BioToy",
    "#BioToyAirPump",
    "#BioToyAirPump1",
    "#BioToyAirPump2",
    "#BioToyAirPump3",
    "#BioToyAirPumpCount",
    "#BioToyCockRing",
    "#BioToyCockRing1",
    "#BioToyCockRing2",
    "#BioToyCockRing3",
    "#BioToyCockRingCount",
    "#BioToyFullOrg",
    "#BioToyFullOrg1",
    "#BioToyFullOrg2",
    "#BioToyFullOrg3",
    "#BioToyFullOrgCount",
    "#BioToyInsertableAnal",
    "#BioToyInsertableAnal1",
    "#BioToyInsertableAnal2",
    "#BioToyInsertableAnal3",
    "#BioToyInsertableAnalCount",
    "#BioToyInsertableVaginal",
    "#BioToyInsertableVaginal1",
    "#BioToyInsertableVaginal2",
    "#BioToyInsertableVaginal3",
    "#BioToyInsertableVaginalCount",
    "#BioToyMetronome1",
    "#BioToyMetronome1_",
    "#BioToyMetronome2",
    "#BioToyMetronome2_",
    "#BioToyOnahole",
    "#BioToyOnahole1",
    "#BioToyOnahole2",
    "#BioToyOnahole3",
    "#BioToyOnaholeCount",
    "#BioToyRuin",
    "#BioToyRuin1",
    "#BioToyRuin2",
    "#BioToyRuin3",
    "#BioToyRuinCount",
    "#BioToyStroker",
    "#BioToyStrokerCustomName",
    "#BioToyStrokerSupport1",
    "#BioToyStrokerSupport1_",
    "#BioToyStrokerSupport2",
    "#BioToyStrokerSupport2_",
    "#BioToyStroker_",
    "#BioToyUnderneath",
    "#BioToyUnderneath1",
    "#BioToyUnderneath2",
    "#BioToyUnderneath3",
    "#BioToyUnderneathCount",
    "#EmlaLockInfo",
]

for command in toy_keywords:
    data["commands"][command] = {
        "name": command,
        "category": "Keyword",
        "parameters": [],
        "description": "Toy related keyword, currently unsupported.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Toy related keyword, currently unsupported.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }


no_usage_keywords = [
    "#BBnB_Ass",
    "#BBnB_Boobs",
    "#BlogImageCount",
    "#BlowjobImageCount",
    "#BoobImageCount",
    "#BoobsImageCount",
    "#ButtImageCount",
    "#ButtsImageCount",
    "#CBTCockCount",
    "#CaptionsImageCount",
    "#CurrentDate",
    "#CurrentDay",
    "#CurrentHour",
    "#CurrentImage",
    "#CurrentMinute",
    "#CurrentMonth",
    "#CurrentTime",
    "#CurrentYear",
    "#DayOfMonth",
    "#DayOfYear",
    "#DislikedImageCount",
    "#DomAvgCockMax",
    "#DomAvgCockMin",
    "#DomBirthdayDay",
    "#DomBirthdayMonth",
    "#DomBirthdayYear",
    "#DomCup",
    "#DomHair",
    "#DomHairLength",
    "#DomLargeCockMin",
    "#DomOrgasmRate",
    "#DomRuinRate",
    "#DomSelfAgeMax",
    "#DomSelfAgeMin",
    "#DomSmallCockMax",
    "#DomSubAgeMax",
    "#DomSubAgeMin",
    "#Dropped",
    "#DroppedCount",
    "#FemdomImageCount",
    "#FirstDropped",
    "#GayImageCount",
    "#GeneralImageCount",
    "#GlitterContact1",
    "#GlitterContact2",
    "#GlitterContact3",
    "#GlitterContact4",
    "#GlitterContact5",
    "#GlitterContact6",
    "#HardcoreImageCount",
    "#ImagePath",
    "#LesbianImageCount",
    "#LezdomImageCount",
    "#LocalImageCount",
    "#MaledomImageCount",
    "#MonthOfYear",
    "#RANDNumber",
    "#RANDNumberHigh",
    "#RANDNumberLow",
    "#RandomSlideshowCategory",
    "#Return_Chastity",
    "#Return_Stroking",
    "#SYS_InterruptsOff",
    "#SYS_MultipleEdgesStop",
    "#SessionCBTCock",
    "#SilverTokens",
    "#SlideshowCount",
    "#SlideshowCurrent",
    "#SlideshowRemaining",
    "#SoftcoreImageCount",
    "#SubBirthdayDay",
    "#SubBirthdayMonth",
    "#SubBirthdayYear",
    "#SubCockSize",
    "#SubEyes",
    "#SubHair",
    "#TaskAmount",
    "#TaskAmountLarge",
    "#TaskCBTTime",
    "#TaskHoldTheEdgeTime",
    "#TaskHours",
    "#TaskMinutes",
    "#TaskSeconds",
    "#TaskStrokes",
    "#TeaseTimeMinutes",
    "#VideoGenres",
    "#VideoOneSloMoTime",
    "#VideoPath",
    "#VideoPosition",
    "#VideosPlayTime",
    "#VideosPlayTimePlusSloMo",
    "#VideosSloMoTime",
]

for command in no_usage_keywords:
    data["commands"][command] = {
        "name": command,
        "category": "Keyword",
        "parameters": [],
        "description": "Unsupported legacy keyword with no recorded usage.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Unsupported legacy keyword with no recorded usage.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }


for command in no_usage_keywords:
    data["commands"][command] = {
        "name": command,
        "category": "Keyword",
        "parameters": [],
        "description": "Unsupported legacy keyword with no recorded usage.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Unsupported legacy keyword with no recorded usage.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

system_provided_vocabulary = [
    "#CumForMe",
    "#Edge",
    "#EdgeHold",
    "#GoodAfternoonSub",
    "#GoodEveningSub",
    "#GoodMorningSub",
    "#GeneralTime",
    "#GreetSub",
    "#Null",
    "#RuinYourOrgasm",
    "#StopStroking",
    "#StartStroking",
    "StopStrokingEdge",
    "#SYS_MultipleEdgesStart",
    "#ExtremeHold",
    "#LongHold",
]

for command in system_provided_vocabulary:
    data["commands"][command] = {
        "name": command,
        "category": "Keyword",
        "parameters": [],
        "description": "System provided vocabulary.",
        "deprecated_by": "",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "System provided vocabulary.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

deprecated_mechanics_keywords = [
    "#RP_CaseNumber",
    "#RP_ChosenCase",
    "#RP_EdgeOffer",
    "#RP_EdgesOwed",
    "#RP_RespondCase",
    "#RP_TokenOffer",
    "#RP_TokensPaid",
    "#BronzeTokens",
    "#SilverTokens",
    "#GoldTokens",
]

for command in deprecated_mechanics_keywords:
    data["commands"][command] = {
        "name": command,
        "category": "Keyword",
        "parameters": [],
        "description": "Unsupported legacy keyword related to mechanics in previous TeaseAI versions.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Unsupported legacy keyword related to mechanics in previous TeaseAi versions.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

deprecated_mechanics_commands = [
    "@AddTokens",
    "@Add100Tokens",
    "@Add10Tokens",
    "@Add1Token",
    "@Add25Tokens",
    "@Add3Tokens",
    "@Add50Tokens",
    "@Add5Tokens",
    "@Remove100Tokens",
    "@RemoveTokens",
    "@Glitter",
]

for command in deprecated_mechanics_commands:
    data["commands"][command] = {
        "name": command,
        "category": "Command",
        "parameters": [],
        "description": "Unsupported legacy command related to mechanics in previous TeaseAI versions.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Unsupported legacy command related to mechanics in previous TeaseAi versions.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

toy_commands = [
    "@BioToyLinearPosition",
    "@BioToyLinearStart",
    "@BioToyStart",
    "@BioToyStartPattern1",
    "@BioToyStartPattern2",
    "@BioToyStartPattern3",
    "@BioToyStopAll",
    "@BioToyStopPattern1",
    "@BioToyStopPattern2",
    "@BioToyStopPattern3",
    "@BioVibToyListen",
    "@BioVibToyStopListen",
    "@HandyInit",
    "@HandyNotReady",
    "@HandyPosition",
    "@HandyReady",
    "@HandyUpDown",
    "@StrokeCycleToy",
    "@StrokeCycleToy2",
    "@EmlaLockLoadInfo",
    "@PlayEStimAudioLoop",
    "@StopEStimAudio",
    "@EStimAudioVolume",
    "@SetSpecificDate",
]

for command in toy_commands:
    data["commands"][command] = {
        "name": command,
        "category": "Command",
        "parameters": [],
        "description": "Toy related command, not currently supported.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Toy related command, not currently supported.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

secondary_metro_commands = [
    "@MetroIsNotRunning",
    "@MetroIsRunning",
    "@MetronomeOff",
    "@MetronomeOn",
    "@MetronomeDown",
    "@MetronomeUp",
    "@MetroPatternOff",
    "@MetroPatternOn",
    "@MetronomeLimit",
    "@MetronomeRandom",
]

for command in secondary_metro_commands:
    data["commands"][command] = {
        "name": command,
        "category": "Command",
        "parameters": [],
        "description": "Secondary metronome related command, not currently supported.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Secondary metrnome related command, not currently supported.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

no_usage_commands = [
    "@CensorVideosOff",
    "@CheckFile",
    "@CheckPlayChc",
    "@CodeWithRepeat",
    "@CountBallTorture",
    "@CountCockTorture",
    "@Cup",
    "@DeleteImage",
    "@DownUpZoom",
    "@EStimMetroEmphasisVolume",
    "@EStimMetroVolume",
    "@EdgeToRuinHoldNoSecret",
    "@EdgeToRuinNoHoldNoSecret",
    "@EndTaunts",
    "@ForceTypo",
    "@HideChat",
    "@DroppedFolderPath",
    "@JumpVideoPosition",
    "@JumpVideoReverse",
    "@Metronome",
    "@NoTypo",
    "@PermSkipExchangeWordsOff",
    "@PermSkipExchangeWordsOn",
    "@PlayEStimAudio",
    "@PlaySecondAudio",
    "@PlaylistOff",
    "@PornAllowedOff",
    "@PornAllowedOn",
    "@ResetVideosPlayTime",
    "@ResetVideosSloMoTime",
    "@SetAdditionalStrokeTime",
    "@SetImageBar",
    "@SkipExchangeWords",
    "@StopSecondAudio",
    "@StrokeSpeedMin",
    "@StrokeSuperSlow",
    "@TnASlides",
    "@VideoBisexual",
    "@VideoBisexualDomme",
    "@VideoCHC",
    "@VideoCHCDomme",
    "@VideoCensored",
    "@VideoFeet",
    "@VideoFeetDomme",
    "@VideoGay",
    "@VideoGayDomme",
    "@VideoJOIDomme",
    "@VideoShemale",
    "@VideoShemaleDomme",
    "@VideoVolume",
]

for command in no_usage_commands:
    data["commands"][command] = {
        "name": command,
        "category": "Command",
        "parameters": [],
        "description": "Unsupported legacy command with no recorded usage.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Unsupported legacy command with no recorded usage.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

toy_command_filters = [
    "@BioToyExistsAirPump",
    "@BioToyExistsAnal",
    "@BioToyExistsCockRing",
    "@BioToyExistsFullOrgasm",
    "@BioToyExistsMetronome1",
    "@BioToyExistsMetronome2",
    "@BioToyExistsOnahole",
    "@BioToyExistsRuinOrgasm",
    "@BioToyExistsStroker",
    "@BioToyExistsStrokerSupport1",
    "@BioToyExistsStrokerSupport2",
    "@BioToyExistsUnderneath",
    "@BioToyExistsVaginal",
    "@BioToyNotExistsAirPump",
    "@BioToyNotExistsAnal",
    "@BioToyNotExistsCockRing",
    "@BioToyNotExistsFullOrgasm",
    "@BioToyNotExistsMetronome1",
    "@BioToyNotExistsMetronome2",
    "@BioToyNotExistsOnahole",
    "@BioToyNotExistsRuinOrgasm",
    "@BioToyNotExistsStroker",
    "@BioToyNotExistsStrokerSupport1",
    "@BioToyNotExistsStrokerSupport2",
    "@BioToyNotExistsUnderneath",
    "@BioToyNotExistsVaginal",
    "@HasNotRemoteToysEnabled",
    "@HasRemoteToysEnabled",
    "@EStimAudioIsNotPlaying",
    "@EStimAudioIsPlaying",
    "@EmlaLock",
]

for command in toy_command_filters:
    data["commands"][command] = {
        "name": command,
        "category": "Command Filter",
        "parameters": [],
        "description": "Toy related command filter, not currently supported.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Toy related command filter, not currently supported.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

no_usage_command_filters = [
    "@ChristmasDay",
    "@ChristmasEve",
    "@DomBirthday",
    "@DomTagAny",
    "@DomTagOr",
    "@EndReached",
    "@FullScreen",
    "@ImageTagAny",
    "@ImageTagOr",
    "@NewYearsDay",
    "@NewYearsEve",
    "@NotFullScreen",
    "@Pace",
    "@Pace1",
    "@Pace8",
    "@PaceNotFastest",
    "@PaceNotSlowest",
    "@RuinTaunt",
    "@SubBirthday",
    "@SubCircumcised",
    "@SubNotCircumcised",
    "@SubNotEdging",
    "@SubNotHoldingTheEdge",
    "@SubNotPierced",
    "@SubPierced",
]

for command in no_usage_command_filters:
    data["commands"][command] = {
        "name": command,
        "category": "Command Filter",
        "parameters": [],
        "description": "Unsupported legacy command filter with recorded usage.",
        "deprecated_by": "@NOP",
        "implemented_by": "",
        "return_value": "string",
        "html_doc": get_html(
            command,
            "Unsupported legacy command filter with no recorded usage.",
            "@NOP",
            command,
            [],
        ),
        "syntax": command,
    }

with open("command_registry2.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
