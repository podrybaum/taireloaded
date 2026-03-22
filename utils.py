from datetime import datetime
import os
import random
import re


def is_valid_filename(filename):
    invalid_chars = r'[<>:"/\\|?*]'
    return not re.search(invalid_chars, filename) and len(filename) <= 255


def convert_string_time_to_seconds(arg):
    if isinstance(arg, int):
        return arg
    int_arg, units = arg.split(" ")
    if units == "minutes":
        return int(int_arg) * 60
    elif units == "hours":
        return int(int_arg) * 60 * 60
    elif units == "days":
        return int(int_arg) * 60 * 60 * 24
    elif units == "seconds":
        return int(int_arg)
    elif units == "weeks":
        return int(int_arg) * 60 * 60 * 24 * 7
    elif units == "months":
        return int(int_arg) * 60 * 60 * 24 * 30
    elif units == "years":
        return int(int_arg) * 60 * 60 * 24 * 365
    else:
        return "invalid units"


def is_image_file(filename):
    if "." not in filename:
        return False
    ext = filename.split(".")[1]
    if ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
        return True
    else:
        return False


def is_video_file(filename):
    ext = filename.split(".")[1]
    if ext in ["mp4", "mpg", "mpeg", "wmv", "mkv"]:
        return True
    return False


def string_from_date(datetime_obj):
    """takes a datetime object and outputs it as a string"""
    return datetime.strftime(datetime_obj, "%m/%d/%Y %I:%M:%S")


def date_from_string(string):
    """takes a string and outputs it as a datatime object"""
    return datetime.strptime(string, "%m/%d/%Y %I:%M:%S")


def random_script(dir):
    if os.path.isdir(dir):
        files = [file for file in os.listdir(dir) if file.endswith(".txt")]
        return os.path.join(dir, random.choice(files))


def random_video(dir):
    if os.path.isdir(dir):
        files = [file for file in os.listdir(dir) if is_video_file(file)]
        return os.path.join(dir, random.choice(files))
