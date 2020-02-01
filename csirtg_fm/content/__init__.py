import magic
import re
import logging
from collections import defaultdict

from csirtg_indicator.utils import resolve_itype

from .utils import is_ascii, is_delimited, is_flat, is_json, is_xml


FILE_TYPE_TESTS = [
    is_xml,
    is_json,
    is_delimited,
    is_flat,
    is_ascii,
]


logger = logging.getLogger(__name__)


def get_mimetype(f):
    try:
        ftype = magic.from_file(f, mime=True)
        return ftype
    except AttributeError:
        pass

    try:
        mag = magic.open(magic.MAGIC_MIME)
    except AttributeError as e:
        raise RuntimeError('unable to detect cached file type')

    mag.load()
    return mag.file(f)


def get_file_type(fname, mime=None):
    if not mime:
        mime = get_mimetype(fname)

    if isinstance(fname, str):
        f = open(fname, 'rb')

    for tt in FILE_TYPE_TESTS:
        f.seek(0)

        try:
            t = tt(f, mime)

        except Exception as e:
            logger.debug(e, exc_info=True)
            continue

        if t:
            return t

    if fname.endswith('.csv') or fname.endswith('.xls'):
        return 'csv'

    if fname.endswith('.tsv'):
        return 'tsv'


get_type = get_file_type


def _is_term(e):
    if e in ['ipv4', 'ipv6', 'url', 'fqdn', 'email', 'md5', 'sha1',
             'sha256', "\n", ""]:
        return

    if re.search(r'\d+', e):
        return

    # we don't care if it's an indicator
    try:
        resolve_itype(e)

    except:
        pass

    else:
        return

    return e


def peek(f, lines=5, delim=','):
    n = lines
    freq_dict = defaultdict(int)

    for l in f.readlines():
        if l.startswith('#'):
            continue

        for e in l.split(delim):
            # if it's a term (eg: word) and not an indicator or symbol
            # add it to the frequency dict..
            if _is_term(e):
                freq_dict[e] += 1

        n -= 1
        if n == 0:
            break

    return sorted(freq_dict, reverse=True)
