import re
import unicodedata


def format_size(bytes_):
    if bytes_ < 1024:
        return str(bytes_)

    kilo = bytes_ / 1024
    if kilo < 1024:
        return "{:.1f}K".format(kilo)

    mega = kilo / 1024
    if mega < 1024:
        return "{:.1f}M".format(mega)

    return "{:.1f}G".format(mega / 1024)


def format_duration(total_seconds):
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = total_seconds % 60

    if hours:
        return "{} h {} min".format(hours, minutes)

    if minutes:
        return "{} min {} sec".format(minutes, seconds)

    return "{} sec".format(seconds)


def read_int(msg, min, max, default):
    msg = msg + " [default {}]: ".format(default)

    while True:
        try:
            val = input(msg)
            if not val:
                return default
            if min <= int(val) <= max:
                return int(val)
        except ValueError:
            pass


def slugify(value):
    re_pattern = re.compile(r'[^\w\s-]', flags=re.U)
    re_spaces = re.compile(r'[-\s]+', flags=re.U)
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re_pattern.sub('', value).strip().lower()
    return re_spaces.sub('-', value)
