import io
import os
import random
from json import dumps, loads
from typing import List
from urllib.parse import urlsplit
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
from PIL import Image
from bus import Bus
from scrapers import BDSMLR_Scraper, GenericScraper, VipergirlsScraper
from tai_exceptions import RuntimeErr
from utils import is_image_file


APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))


class Slideshow:
    def __init__(self):
        self.slides = []
        self.randomize = False
        self.merge_subfolders = False
        self.current_slide = None
        self._dont_advance = False
        Bus.emit("randomize_value_requested", self, "randomize")
        self.index = 0
        self.live = False
        Bus.sub("end_tease", self._on_end_tease)
        Bus.register("pause_slideshow", self._on_pause_slideshow)
        Bus.register("unpause_slideshow", self._on_start_slideshow)
        Bus.register("start_slideshow", self._on_start_slideshow)
        Bus.register("next_slide", self.advance)
        Bus.register("new_slideshow", self._load_slides)
        Bus.register("stop_slideshow", self._on_end_tease)
        Bus.register("img_tags_requested", self._on_img_tags_requested)
        Bus.register("show_image_tag", self._on_show_image_tag)
        Bus.register("show_image_tag_any", self._on_show_image_tag_any)
        Bus.sub("new_message", self._on_new_message)
        Bus.register("dont_advance", lambda: setattr(self, "_dont_advance", True))
        Bus.sub("show_image", lambda img: setattr(self, "current_image", img))

    def _on_new_message(self, sender, message):
        if sender != "You" and not self._dont_advance:
            return self.advance()
        self._dont_advance = False

    def _on_show_image_tag_any(self, tags):
        slides = [slide for slide in self.slides if any(tags in slide.tags)]
        if len(slides) > 0:
            Bus.emit("show_image", random.choice(slides))

    def _on_show_image_tag(self, tags):
        slides = [slide for slide in self.slides if all(tags in slide.tags)]
        if len(slides) > 0:
            Bus.emit("show_image", random.choice(slides))

    def _on_img_tags_requested(self, empty_list):
        empty_list.extend(self.current_slide.tags)

    def _on_end_tease(self):
        self.live = False
        Bus.emit("hide_image")

    def advance(self):
        if not self.live:
            return
        Bus.emit("show_image", self.slides[self.index])
        self.index += 1
        if self.index > len(self.slides) - 1:
            self.index = 0
            if self._randomize:
                random.shuffle(self.slides)

    def _on_pause_slideshow(self):
        self.live = False

    def _on_start_slideshow(self):
        self.live = True
        self.advance()

    def _load_slides(self, source: List):
        """if source is a list of TAI_Image objects, assign it to self._slides.<br>
        if source is a list of paths, iterate through the provided paths, creating TAI_Image objects"""
        Bus.emit("merge_subfolders_value_requested", self, "merge_subfolders")
        Bus.emit("randomize_value_requested", self, "randomize")
        source = list(source)
        if isinstance(source[0], TAI_Image):
            self.slides = source
            return
        self.slides = []
        for folder in [os.walk(path) for path in source]:
            self.slides.extend(self.get_image_objects(folder))

    def get_image_objects(self, folder):
        """takes a tuple from the output of os.walk and returns a list of TAI_Image objects
        if 'merge_subfolders' is True in the user config, the list includes images found in subfolders"""
        dirpath, dirnames, filenames = folder
        img_filenames = [file for file in filenames if is_image_file(file)]
        tags = []
        img_objects = []
        if os.path.isfile(os.path.join(dirpath, "ImageTags.txt")):
            with open(os.path.join(dirpath, "ImageTags.txt")) as f:
                tags = f.readlines()
        if len(tags) > 0:
            for line in tags:
                line = line.split()
                if line[0] in img_filenames:
                    img_filenames.remove(line[0])
                    img_objects.append(TAI_Image(os.path.join(dirpath, line[0]), line[1:]))
        for img in img_filenames:
            img_objects.append(TAI_Image(os.path.join(dirpath, img)))
        if self.merge_subfolders:
            for folder in dirnames:
                img_objects.extend[self.get_image_objects(os.walk(os.path.join(dirpath, folder)))]
        return img_objects


class TAI_Image:
    def __init__(self, source, tags=None):
        self.source = source
        self.tags = tags
        self.img = None
        self.fetch()

    def fetch(self):

        if isinstance(self.source, io.BytesIO):
            self.img = CoreImage(self.source)
            return
        if os.path.isfile(self.source):
            pil_img = Image.open(self.source).convert("RGBA")
            width, height = pil_img.size
            raw = pil_img.tobytes()
            texture = Texture.create(size=(width, height), colorfmt="rgba")
            texture.blit_buffer(raw, colorfmt="rgba", bufferfmt="ubyte")
            texture.flip_vertical()
            self.img = type("_TexWrapper", (), {"texture": texture})()


class URL_File:
    def __init__(self, url, user=None, password=None):
        o = urlsplit(url, scheme="https")
        self.url = "".join(o)
        self.url = f"{o.netloc if o.netloc else o.path} {'/' + o.path if o.netloc and o.path else ''} {'?' + o.query if o.query else ''} {'#' + o.fragment if o.fragment else ''}".strip()
        self.file = f"url_files\\{url}.json"
        self.img_dir = f"url_files\\{url}"
        self.user = user
        self.password = password
        self.resolved = False
        self.imgs_as_urls = []
        self.imgs_as_bytes = []
        self.map = {}
        if not os.path.isfile(self.file):
            with open(self.file, "w") as f:
                dict = self.__dict__
                f.write(dumps(dict))
        else:
            with open(self.file, "r") as f:
                json_dict = loads(f.read())
                self.user = json_dict["user"]
                self.password = json_dict["password"]
                self.resolved = json_dict["resolved"]
                self.map = json_dict["map"]
                self.imgs_as_urls = list(self.map.keys())
        self.scraper = self.get_scraper()
        for v in self.map.values():
            if v == "":
                self.resolved = False
        if not self.resolved:
            self.get_images()

    @classmethod
    def from_json(cls, file):
        if not file.endswith(".json"):
            raise ValueError("Argument to from_json must be a json file.")
        with open(os.path.join(APPLICATION_ROOT, "url_files", file), "r") as f:
            cls_json = loads(f.read())
            return cls(url=cls_json["url"])

    def load(self):
        img_objects = []
        for image in self.imgs_as_urls:
            path_to_bytes = self.map[image]
            if not os.path.isfile(path_to_bytes):
                print("File not found:", path_to_bytes)

            img_objects.append(TAI_Image(path_to_bytes))
        Bus.emit("new_slideshow", img_objects)

    def get_images(self):
        imgs = self.scraper.fetch()
        for img in imgs:
            img_data, img_url = img
            self.imgs_as_urls.append(img_url)
            self.imgs_as_bytes.append(Image.open(img_data))
        self.resolved = True
        if not os.path.isdir(self.img_dir):
            os.mkdir(self.img_dir)
        for i, img in enumerate(self.imgs_as_bytes):
            filename = self.imgs_as_urls[i].split("/")[-1]
            ext = filename.split(".")[-1]
            if img.mode in ("RGBA", "P"):
                self.imgs_as_bytes[i] = Image.composite(img, Image.new("RGB", img.size, "white"), img)
                ext = "jpeg"
            if ext.upper() == "JPG":
                filename = filename.replace(ext, "jpeg")
                ext = "jpeg"
            self.map[self.imgs_as_urls[i]] = os.path.join(self.img_dir, filename)
            if not os.path.isfile(os.path.join(self.img_dir, filename)):
                try:
                    self.imgs_as_bytes[i].save(os.path.join(self.img_dir, filename), ext)
                except KeyError as e:
                    print(e)
        with open(self.file, "w") as f:
            f.write(
                dumps(
                    {
                        "url": self.url,
                        "user": self.user,
                        "password": self.password,
                        "resolved": self.resolved,
                        "map": self.map,
                    }
                )
            )

    def get_scraper(self):
        if self.get_domain() == "bdsmlr.com":
            if not self.user or not self.password:
                RuntimeErr("Username and password are required for bdsmlr.com URL files").throw()
            return BDSMLR_Scraper(url=self.url, user=self.user, password=self.password)
        if self.get_domain() == "vipergirls.to":
            return VipergirlsScraper(url=self.url)
        return GenericScraper(self.url)

    def get_domain(self):
        """Extracts the clean domain (e.g., example.com) from a URL."""
        if urlsplit(self.url, scheme="https").hostname is None:
            return "".join(urlsplit(self.url, scheme="https").path.split(".", 1)[1:])
        return urlsplit(self.url, scheme="https").hostname
