
import os
from sqlalchemy.ext.declarative import declarative_base
from csirtg_fm.constants import CACHE_PATH

BASE = declarative_base()

TRACE = False
if os.getenv('CSIRTG_FM_ARCHIVER_TRACE', '0') == '1':
    TRACE = True

CLEANUP_DAYS = os.getenv('CSIRTG_FM_ARCHIVER_CLEANUP_DAYS', 90)

# http://stackoverflow.com/q/9671490/7205341
SYNC = os.environ.get('CIF_STORE_SQLITE_SYNC', 'NORMAL')

# https://www.sqlite.org/pragma.html#pragma_cache_size
CACHE_SIZE = os.environ.get('CIF_STORE_SQLITE_CACHE_SIZE', 512000000)  # 512MB

DB_FILE = os.path.join(CACHE_PATH, 'fm.db')
