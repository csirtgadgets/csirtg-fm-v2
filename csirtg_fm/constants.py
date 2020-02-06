import os.path
import tempfile
import re

from ._version import get_versions
VERSION = get_versions()['version']
del get_versions


TEMP_DIR = os.path.join(tempfile.gettempdir())
RUNTIME_PATH = os.getenv('CSIRTG_FM_RUNTIME_PATH', TEMP_DIR)
RUNTIME_PATH = os.path.join(RUNTIME_PATH)

FM_CACHE = os.path.join(RUNTIME_PATH, 'fm')
FM_CACHE = os.getenv('CSIRTG_FM_CACHE_PATH', FM_CACHE)
CACHE_PATH = FM_CACHE

FM_RULES_PATH = os.getenv('CSIRTG_FM_RULES_PATH',
                          os.path.join(os.getcwd(), 'rules'))

FIREBALL_SIZE = os.getenv('CSIRTG_FM_FIREBALL_SIZE', 500)
if FIREBALL_SIZE == '':
    FIREBALL_SIZE = 500


LOGLEVEL = os.getenv('CSIRTG_FM_LOGLEVEL', 'ERROR')

RE_CACHE_TYPES = re.compile('([\w.-]+\.(csv|zip|txt|gz))$')
RE_FQDN = r'((?!-))(xn--)?[a-z0-9][a-z0-9-_\.]{0,245}[a-z0-9]{0,1}\.(xn--)?([a-z0-9\-]{1,61}|[a-z0-9-]{1,30}\.[a-z]{2,})'
