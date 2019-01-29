import re
import unicodedata


def slugify(value):
    re_pattern = re.compile(r'[^\w\s-]', flags=re.U)
    re_spaces = re.compile(r'[-\s]+', flags=re.U)
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re_pattern.sub('', value).strip().lower()
    return re_spaces.sub('-', value)
