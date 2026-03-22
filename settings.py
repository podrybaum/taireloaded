from datetime import datetime
import utils
from bus import Bus
from message_classes import UserMessage


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
        self.birthday_day = 0
        self.birthday_month = 0
        self.birthday_year = 0
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
        self.general_video = dict["general_video"]

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
        self._avatar = dict["_avatar"]
        self._image_folder = dict["_image_folder"]

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
        self.last_orgasm_date = utils.date_from_string(dict["last_orgasm_date"])
        self.last_ruin_date = utils.date_from_string(dict["last_ruin_date"])
        self.name = dict["name"]


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
    "min_tease_length": 15 * 60,
    "max_tease_length": 45 * 60,
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
    "use_avg_as_threshold": False,
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
}


class Settings:
    def __init__(self):
        self.Domme = DommeObj()
        self.Domme.from_dict(domme_dict)
        self.Contact1 = Contact(1)
        self.Contact1.from_dict(contact1_dict)
        self.Contact2 = Contact(2)
        self.Contact2.from_dict(contact1_dict)
        self.Contact3 = Contact(3)
        self.Contact3.from_dict(contact1_dict)
        self.Contact4 = Contact(4)
        self.Contact4.from_dict(contact1_dict)
        self.Contact5 = Contact(5)
        self.Contact5.from_dict(contact1_dict)
        self.Contact6 = Contact(6)
        self.Contact6.from_dict(contact1_dict)
        self.Sub = Sub()
        self.Sub.from_dict(sub_dict)
        self.current_personality = settings_dict["current_personality"]
        self.taunt_cycle_min = settings_dict["taunt_cycle_min"]
        self.taunt_cycle_max = settings_dict["taunt_cycle_max"]
        self.min_tease_length = settings_dict["min_tease_length"]
        self.max_tease_length = settings_dict["max_tease_length"]
        self.domme_delete = False
        self.boobs_images = settings_dict["boobs_images"]
        self.butts_images = settings_dict["butts_images"]
        self.joi_video = settings_dict["joi_video"]
        self.general_images = settings_dict["general_images"]
        self.captions_images = settings_dict["captions_images"]
        self.maledom_images = settings_dict["maledom_images"]
        self.gay_images = settings_dict["gay_images"]
        self.hentai_images = settings_dict["hentai_images"]
        self.lezdom_images = settings_dict["lezdom_images"]
        self.femdom_images = settings_dict["femdom_images"]
        self.blowjob_images = settings_dict["blowjob_images"]
        self.lesbian_images = settings_dict["lesbian_images"]
        self.softcore_images = settings_dict["softcore_images"]
        self.hardcore_iamges = settings_dict["hardcore_images"]
        self.joi_video = settings_dict["joi_video"]
        self.hardcore_video = settings_dict["hardcore_video"]
        self.softcore_video = settings_dict["softcore_video"]
        self.lesbian_video = settings_dict["lesbian_video"]
        self.blowjob_video = settings_dict["blowjob_video"]
        self.femdom_video = settings_dict["femdom_video"]
        self.femsub_video = settings_dict["femsub_video"]
        self.ch_video = settings_dict["ch_video"]
        self.general_video = settings_dict["general_video"]
        self.randomize_slides = settings_dict["randomize_slides"]
        self._edge_start = None
        self.writing_task_lines_min = settings_dict["writing_task_lines_min"]
        self.writing_task_lines_max = settings_dict["writing_task_lines_max"]
        self.offline_mode = settings_dict["offline_mode"]
        Bus.sub("new_message", self._on_new_message)
        Bus.register("randomize_value_requested", self._on_randomize_value_requested)
        Bus.register("merge_subfolders_value_requested", self._on_merge_subfolders_value_requested)
        Bus.register("offline_mode_setting_requested", self._on_offline_mode_setting_requested)
        Bus.register("get_current_personality", self._on_get_current_personality)

    def _on_get_current_personality(self, pers_dict):
        pers_dict["personality"] = self.current_personality

    def _on_offline_mode_setting_requested(self, obj):
        obj["offline_mode"] = self.offline_mode

    def _on_merge_subfolders_value_requested(self, obj, attr):
        setattr(obj, attr, self.settings.merge_subfolders)

    def _on_randomize_value_requested(self, obj, attr):
        setattr(obj, attr, self.randomize_slides)

    def _on_edge_start(self):
        self._edge_start = datetime.now()

    def _on_new_message(self, message):
        if isinstance(message, UserMessage):
            for word in ["edge", "edging"]:
                if word in message.text and self._edge_start is not None:
                    delta_time = datetime.now() - self._edge_start
                    self.Sub._cumulative_edge_time += delta_time.seconds
                    self.Sub._edges_all_time += 1
                    self.Sub.avg_edge_time = self.Sub._cumulative_edge_time / self.Sub._edges_all_time
                    self._edge_start = None

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

    def domme_namespace(self, attr):
        return getattr(self.Domme, attr)

    def set(self, name, value):
        setattr(self, name, value)

    def get(self, name):
        return getattr(self, name, None)
