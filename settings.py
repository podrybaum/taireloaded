import os
import json
import utils
from bus import Bus

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


ALLOWS_ORGASMS = {1: "Always Allows", 2: "Often Allows", 3: "Sometimes Allows", 4: "Rarely Allows", 5: "Never Allows"}

RUINS_ORGASMS = {1: "Always Ruins", 2: "Often Ruins", 3: "Sometimes Ruins", 4: "Rarely Ruins", 5: "Never Ruins"}


class DommeObj:
    def __init__(self):
        self._avatar = None
        self._bad_mood_pet_names = []
        self._good_mood_pet_names = []
        self._image_folder = ""
        self._neutral_mood_pet_names = []
        self.age = 0
        self.allows_orgasms = 1
        self.allows_orgasms_string = ALLOWS_ORGASMS[self.allows_orgasms]
        self.apathy_level = 0
        self.avg_cock_size_max = 0
        self.avg_cock_size_min = 0
        self.cfnm = False
        self.crazy = False
        self.cup_size = ""
        self.degrading = False
        self.eyes = ""
        self.hair_color = ""
        self.hair_length = ""
        self.honorific = ""
        self.honorifices = self.honorific + "es"
        self.level = 0
        self.mood_index_max = 0
        self.mood_index_min = 0
        self.name = ""
        self.ruins_orgasms = 1
        self.ruins_orgasms_string = RUINS_ORGASMS[self.ruins_orgasms]
        self.sadistic = False
        self.short_name = ""
        self.supremacist = False
        self.vulgar = False
        self.joi_video = ""
        self.hardcore_video = ""
        self.softcore_video = ""
        self.lesbian_video = ""
        self.blowjob_video = ""
        self.femdom_video = ""
        self.femsub_video = ""
        self.ch_video = ""
        self.general_video = ""

    def from_dict(self, dict):
        self._avatar = dict["_avatar"]
        self._image_folder = dict["_image_folder"]
        self.name = dict["name"]
        self.honorific = dict["honorific"]
        self.apathy_level = dict["apathy_level"]
        self.level = dict["level"]
        self.cup_size = dict["cup_size"]
        self.eyes = dict["eyes"]
        self.hair_color = dict["hair_color"]
        self.hair_length = dict["hair_length"]
        self.birthday_day = dict["birthday_day"]
        self.birthday_month = dict["birthday_month"]
        self.birthday_year = dict["birthday_year"]
        self.avg_cock_size_min = dict["avg_cock_size_min"]
        self.avg_cock_size_max = dict["avg_cock_size_max"]
        self.allows_orgasms = dict["allows_orgasms"]
        self.ruins_orgasms = dict["ruins_orgasms"]
        self._good_mood_pet_names = dict["_good_mood_pet_names"]
        self._neutral_mood_pet_names = dict["_neutral_mood_pet_names"]
        self._bad_mood_pet_names = dict["_bad_mood_pet_names"]
        self.crazy = dict["crazy"]
        self.vulgar = dict["vulgar"]
        self.degrading = dict["degrading"]
        self.cfnm = dict["cfnm"]
        self.supremacist = dict["supremacist"]
        self.sadistic = dict["sadistic"]
        self.mood_index_min = dict["mood_index_min"]
        self.mood_index_max = dict["mood_index_max"]
        self.age = dict["age"]
        self.short_name = dict["short_name"]
        self.joi_video = dict["joi_video"]
        self.hardcore_video = dict["hardcore_video"]
        self.softcore_video = dict["softcore_video"]
        self.lesbian_video = dict["lesbian_video"]
        self.blowjob_video = dict["blowjob_video"]
        self.femdom_video = dict["femdom_video"]
        self.femsub_video = dict["femsub_video"]
        self.ch_video = dict["ch_video"]
        self.general_video = dict.get("general_video", "")

    def to_dict(self):
        return {
            "_avatar": self._avatar,
            "_image_folder": self._image_folder,
            "name": self.name,
            "honorific": self.honorific,
            "apathy_level": self.apathy_level,
            "level": self.level,
            "cup_size": self.cup_size,
            "eyes": self.eyes,
            "hair_color": self.hair_color,
            "hair_length": self.hair_length,
            "birthday_day": self.birthday_day,
            "birthday_month": self.birthday_month,
            "birthday_year": self.birthday_year,
            "avg_cock_size_min": self.avg_cock_size_min,
            "avg_cock_size_max": self.avg_cock_size_max,
            "allows_orgasms": self.allows_orgasms,
            "ruins_orgasms": self.ruins_orgasms,
            "_good_mood_pet_names": self._good_mood_pet_names,
            "_neutral_mood_pet_names": self._neutral_mood_pet_names,
            "_bad_mood_pet_names": self._bad_mood_pet_names,
            "crazy": self.crazy,
            "vulgar": self.vulgar,
            "degrading": self.degrading,
            "cfnm": self.cfnm,
            "supremacist": self.supremacist,
            "sadistic": self.sadistic,
            "mood_index_min": self.mood_index_min,
            "mood_index_max": self.mood_index_max,
            "age": self.age,
            "short_name": self.short_name,
            "joi_video": self.joi_video,
            "hardcore_video": self.hardcore_video,
            "softcore_video": self.softcore_video,
            "lesbian_video": self.lesbian_video,
            "blowjob_video": self.blowjob_video,
            "femdom_video": self.femdom_video,
            "femsub_video": self.femsub_video,
            "ch_video": self.ch_video,
            "general_video": self.general_video,
        }

    def __str__(self):
        return self.name


class Contact:
    # attributes without a leading underscore are exposed to the scripting context
    def __init__(self, number):
        self._avatar = None
        self._image_folder = None
        self._number = number
        self.honorific = ""
        self.name = ""

    def from_dict(self, dict):
        self.name = dict["name"]
        self.honorific = dict["honorific"]
        self._number = dict["_number"]
        self._avatar = dict.get("_avatar")
        self._image_folder = dict.get("_image_folder")

    def to_dict(self):
        return {
            "name": self.name,
            "honorific": self.honorific,
            "_number": self._number,
            "_avatar": self._avatar,
            "_image_folder": self._image_folder,
        }

    def __str__(self):
        return self.name


class Sub:
    def __init__(self):
        self.min_edge_hold_time = 0
        self.max_edge_hold_time = 0
        self.min_long_hold_time = 0
        self.max_long_hold_time = 0
        self.min_extreme_hold_time = 0
        self.max_extreme_hold_time = 0
        self.age = 0
        self.cock_size = 0
        self.use_avg_as_threshold = False
        self.has_chastity = False
        self.chastity_piercing = False
        self.chastity_spikes = False
        self.CockTorture = False
        self.BallTorture = False
        self.cbt_level = 0
        self.avg_edge_time = 0
        self.long_edge_threshold = 0
        self._edges_all_time = 0
        self._cumulative_edge_time = 0
        self.last_orgasm_date = None
        self.last_ruin_date = None
        self.name = ""
        self.long_edge_interrupts = True

    def from_dict(self, dict):
        self.min_edge_hold_time = dict["min_edge_hold_time"]
        self.max_edge_hold_time = dict["max_edge_hold_time"]
        self.min_long_hold_time = dict["min_long_hold_time"]
        self.max_long_hold_time = dict["max_long_hold_time"]
        self.min_extreme_hold_time = dict["min_extreme_hold_time"]
        self.max_extreme_hold_time = dict["max_extreme_hold_time"]
        self.age = dict["age"]
        self.cock_size = dict["cock_size"]
        self.use_avg_as_threshold = dict["use_avg_as_threshold"]
        self.has_chastity = dict["has_chastity"]
        self.chastity_piercing = dict["chastity_piercing"]
        self.chastity_spikes = dict["chastity_spikes"]
        self.CockTorture = dict["CockTorture"]
        self.BallTorture = dict["BallTorture"]
        self.cbt_level = dict["cbt_level"]
        self.avg_edge_time = dict["avg_edge_time"]
        self.long_edge_threshold = dict["long_edge_threshold"]
        self._edges_all_time = dict["_edges_all_time"]
        self._cumulative_edge_time = dict["_cumulative_edge_time"]
        self.last_orgasm_date = (
            utils.date_from_string(dict["last_orgasm_date"]) if dict.get("last_orgasm_date") else None
        )
        self.last_ruin_date = utils.date_from_string(dict["last_ruin_date"]) if dict.get("last_ruin_date") else None
        self.name = dict.get("name", "")
        self.long_edge_interrupts = dict.get("long_edge_interrupts", True)

    def to_dict(self):
        return {
            "min_edge_hold_time": self.min_edge_hold_time,
            "max_edge_hold_time": self.max_edge_hold_time,
            "min_long_hold_time": self.min_long_hold_time,
            "max_long_hold_time": self.max_long_hold_time,
            "min_extreme_hold_time": self.min_extreme_hold_time,
            "max_extreme_hold_time": self.max_extreme_hold_time,
            "age": self.age,
            "cock_size": self.cock_size,
            "use_avg_as_threshold": self.use_avg_as_threshold,
            "has_chastity": self.has_chastity,
            "chastity_piercing": self.chastity_piercing,
            "chastity_spikes": self.chastity_spikes,
            "CockTorture": self.CockTorture,
            "BallTorture": self.BallTorture,
            "cbt_level": self.cbt_level,
            "avg_edge_time": self.avg_edge_time,
            "long_edge_threshold": self.long_edge_threshold,
            "_edges_all_time": self._edges_all_time,
            "_cumulative_edge_time": self._cumulative_edge_time,
            "last_orgasm_date": utils.string_from_date(self.last_orgasm_date) if self.last_orgasm_date else None,
            "last_ruin_date": utils.string_from_date(self.last_ruin_date) if self.last_ruin_date else None,
            "name": self.name,
            "long_edge_interrupts": self.long_edge_interrupts,
        }


# stubbing for now
domme_dict = {
    "name": "Ashley",
    "honorific": "Mistress",
    "apathy_level": 1,
    "level": 1,
    "cup_size": "A",
    "eyes": "Blue",
    "hair_color": "Brown",
    "hair_length": "Long",
    "birthday_day": 1,
    "birthday_month": 1,
    "birthday_year": 2000,
    "avg_cock_size_min": 3,
    "avg_cock_size_max": 6,
    "allows_orgasms": 1,
    "ruins_orgasms": 5,
    "_good_mood_pet_names": ["bitch", "loser"],
    "_neutral_mood_pet_names": ["sissy", "tiny", "pump junkie", "bitch"],
    "_bad_mood_pet_names": ["fuckface", "pussy"],
    "crazy": False,
    "vulgar": True,
    "degrading": True,
    "cfnm": False,
    "supremacist": False,
    "sadistic": False,
    "mood_index_min": 3,
    "mood_index_max": 8,
    "age": 18,
    "short_name": "Ash",
    "_avatar": "ui_resources\\domme_avatar.png",
    "_image_folder": "ui_resources",
    "joi_video": "",
    "hardcore_video": "",
    "softcore_video": "",
    "lesbian_video": "",
    "blowjob_video": "",
    "femdom_video": "",
    "femsub_video": "",
    "ch_video": "",
    "general_video": "",
}

contact1_dict = {"name": "Amanda", "honorific": "Miss", "_image_folder": "", "_avatar": None, "_number": 1}

settings_dict = {
    "current_personality": "Joi",
    "taunt_cycle_min": 60,
    "taunt_cycle_max": 300,
    "min_tease_length": 15,
    "max_tease_length": 45,
    "domme_delete": False,
    "boobs_images": "",
    "butts_images": "",
    "general_images": "",
    "captions_images": "",
    "maledom_images": "",
    "gay_images": "",
    "hentai_images": "",
    "lezdom_images": "",
    "femdom_images": "",
    "blowjob_images": "",
    "lesbian_images": "",
    "softcore_images": "",
    "hardcore_images": "",
    "joi_video": "",
    "hardcore_video": "",
    "softcore_video": "",
    "lesbian_video": "",
    "blowjob_video": "",
    "femdom_video": "",
    "femsub_video": "",
    "ch_video": "",
    "general_video": "",
    "randomize_slides": True,
    "writing_task_lines_min": 10,
    "writing_task_lines_max": 20,
    "orgasm_lock_date": "05/09/2026 09:15:40",
    "offline_mode": False,
    "interrupt_long_edge": True,
}

sub_dict = {
    "name": "Brandon",
    "min_edge_hold_time": 5,
    "max_edge_hold_time": 10,
    "min_long_hold_time": 20,
    "max_long_hold_time": 30,
    "min_extreme_hold_time": 40,
    "max_extreme_hold_time": 60,
    "age": 18,
    "cock_size": 5,
    "use_avg_as_threshold": True,
    "has_chastity": False,
    "chastity_piercing": False,
    "chastity_spikes": False,
    "CockTorture": False,
    "BallTorture": False,
    "cbt_level": 1,
    "cbt_task_amount_min": 1,
    "cbt_task_amount_max": 5,
    "avg_edge_time": 15,
    "long_edge_threshold": 5,
    "_edges_all_time": 100,
    "_cumulative_edge_time": 1000,
    "last_orgasm_date": "03/09/2026 09:15:40",
    "last_ruin_date": "03/09/2026 09:15:40",
    "long_edge_interrupts": True,
}


class Settings:
    def __init__(self):
        self.Domme = DommeObj()
        self.Contact1 = Contact(1)
        self.Contact2 = Contact(2)
        self.Contact3 = Contact(3)
        self.Contact4 = Contact(4)
        self.Contact5 = Contact(5)
        self.Contact6 = Contact(6)
        self.Sub = Sub()
        self.Variables = {}
        self.Flags = {}
        self.load()

        self.Domme.avatar_backup = None
        self.Domme.name_backup = None
        self._edge_start = None

        Bus.register("save_settings", lambda *args: self.save())
        Bus.register("randomize_value_requested", self._on_randomize_value_requested)
        Bus.register("merge_subfolders_value_requested", self._on_merge_subfolders_value_requested)
        Bus.register("offline_mode_setting_requested", self._on_offline_mode_setting_requested)
        Bus.register("get_current_personality", self._on_get_current_personality)
        Bus.register("set_personality", self._on_set_personality)

    def load(self):
        filepath = os.path.join(APPLICATION_ROOT, "settings.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
            except Exception:
                data = self._default_dict()
        else:
            data = self._default_dict()

        self.Domme.from_dict(data.get("Domme", domme_dict))
        self.Contact1.from_dict(data.get("Contact1", contact1_dict))
        self.Contact2.from_dict(data.get("Contact2", contact1_dict))
        self.Contact3.from_dict(data.get("Contact3", contact1_dict))
        self.Contact4.from_dict(data.get("Contact4", contact1_dict))
        self.Contact5.from_dict(data.get("Contact5", contact1_dict))
        self.Contact6.from_dict(data.get("Contact6", contact1_dict))
        self.Sub.from_dict(data.get("Sub", sub_dict))

        self.current_personality = data.get("current_personality", settings_dict["current_personality"])
        self.taunt_cycle_min = data.get("taunt_cycle_min", settings_dict["taunt_cycle_min"])
        self.taunt_cycle_max = data.get("taunt_cycle_max", settings_dict["taunt_cycle_max"])
        self.min_tease_length = data.get("min_tease_length", settings_dict["min_tease_length"] * 60)
        self.max_tease_length = data.get("max_tease_length", settings_dict["max_tease_length"] * 60)
        self.domme_delete = data.get("domme_delete", settings_dict.get("domme_delete", False))

        for k in [
            "boobs_images",
            "butts_images",
            "joi_video",
            "general_images",
            "captions_images",
            "maledom_images",
            "gay_images",
            "hentai_images",
            "lezdom_images",
            "femdom_images",
            "blowjob_images",
            "lesbian_images",
            "softcore_images",
            "hardcore_images",
            "hardcore_video",
            "softcore_video",
            "lesbian_video",
            "blowjob_video",
            "femdom_video",
            "femsub_video",
            "ch_video",
            "general_video",
        ]:
            setattr(self, k, data.get(k, settings_dict.get(k, "")))
            if k == "hardcore_images":
                self.hardcore_iamges = data.get(k, settings_dict.get(k, ""))

        self.randomize_slides = data.get("randomize_slides", settings_dict["randomize_slides"])
        self.interrupt_long_edge = data.get("interrupt_long_edge", settings_dict["interrupt_long_edge"])
        self.writing_task_lines_min = data.get("writing_task_lines_min", settings_dict["writing_task_lines_min"])
        self.writing_task_lines_max = data.get("writing_task_lines_max", settings_dict["writing_task_lines_max"])
        self.offline_mode = data.get("offline_mode", settings_dict["offline_mode"])

        self.Variables = data.get("Variables", {})
        self.Flags = data.get("Flags", {})

    def save(self):
        filepath = os.path.join(APPLICATION_ROOT, "settings.json")
        temp_path = filepath + ".tmp"
        try:
            with open(temp_path, "w") as f:
                json.dump(self.to_dict(), f, indent=4)
            if os.path.exists(filepath):
                os.replace(temp_path, filepath)
            else:
                os.rename(temp_path, filepath)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def to_dict(self):
        base = self._default_dict()
        base["Domme"] = self.Domme.to_dict()
        base["Contact1"] = self.Contact1.to_dict()
        base["Contact2"] = self.Contact2.to_dict()
        base["Contact3"] = self.Contact3.to_dict()
        base["Contact4"] = self.Contact4.to_dict()
        base["Contact5"] = self.Contact5.to_dict()
        base["Contact6"] = self.Contact6.to_dict()
        base["Sub"] = self.Sub.to_dict()

        base["current_personality"] = self.current_personality
        base["taunt_cycle_min"] = self.taunt_cycle_min
        base["taunt_cycle_max"] = self.taunt_cycle_max
        base["min_tease_length"] = self.min_tease_length
        base["max_tease_length"] = self.max_tease_length
        base["domme_delete"] = self.domme_delete

        for k in [
            "boobs_images",
            "butts_images",
            "joi_video",
            "general_images",
            "captions_images",
            "maledom_images",
            "gay_images",
            "hentai_images",
            "lezdom_images",
            "femdom_images",
            "blowjob_images",
            "lesbian_images",
            "softcore_images",
            "hardcore_images",
            "hardcore_video",
            "softcore_video",
            "lesbian_video",
            "blowjob_video",
            "femdom_video",
            "femsub_video",
            "ch_video",
            "general_video",
        ]:
            val = getattr(self, k, "")
            base[k] = val
        base["hardcore_images"] = getattr(self, "hardcore_iamges", base["hardcore_images"])

        base["randomize_slides"] = self.randomize_slides
        base["interrupt_long_edge"] = self.interrupt_long_edge
        base["writing_task_lines_min"] = self.writing_task_lines_min
        base["writing_task_lines_max"] = self.writing_task_lines_max
        base["offline_mode"] = self.offline_mode
        base["Variables"] = self.Variables
        base["Flags"] = self.Flags
        return base

    def _default_dict(self):
        d = settings_dict.copy()
        d["Domme"] = domme_dict
        d["Contact1"] = contact1_dict
        d["Contact2"] = contact1_dict
        d["Contact3"] = contact1_dict
        d["Contact4"] = contact1_dict
        d["Contact5"] = contact1_dict
        d["Contact6"] = contact1_dict
        d["Sub"] = sub_dict
        return d

    def _on_set_personality(self, name):
        self.current_personality = name

    def _on_get_current_personality(self, pers_dict):
        pers_dict["personality"] = self.current_personality

    def _on_offline_mode_setting_requested(self, obj):
        obj["offline_mode"] = self.offline_mode

    def _on_merge_subfolders_value_requested(self, obj, attr):
        setattr(obj, attr, self.settings.merge_subfolders)

    def _on_randomize_value_requested(self, obj, attr):
        setattr(obj, attr, self.randomize_slides)

    def contact_namespace(self, id, attr):
        contact = None
        match id:
            case 1:
                contact = self.Contact1
            case 2:
                contact = self.Contact2
            case 3:
                contact = self.Contact3
            case 4:
                contact = self.Contact4
            case 5:
                contact = self.Contact5
            case 6:
                contact = self.Contact6
        if attr == "object":
            return contact
        return getattr(contact, attr)

    def domme_id_to_object(self, id):
        if id == "D":
            return self.Domme
        elif id > 0 and id < 7:
            return self.contact_namespace(id, "object")

    def domme_namespace(self, attr):
        return getattr(self.Domme, attr)

    def set(self, name, value):
        setattr(self, name, value)

    def get(self, name):
        return getattr(self, name, None)
