from collections import OrderedDict
import logging

from csirtg_indicator.utils import resolve_itype

logger = logging.getLogger(__name__)


def is_ascii(f, mime):
    if mime.startswith(('text/plain', 'ASCII text')):
        return 'pattern'


def is_flat(f, mime):
    if not is_ascii(f, mime):
        return

    n = 5
    for l in f.readlines():
        if isinstance(l, bytes):
            l = l.decode('utf-8')

        if l.startswith('#'):
            continue

        try:
            resolve_itype(l.rstrip("\n"))
        except Exception as e:
            logger.debug(e)
            return

        n -= 1
        if n == 0:
            break

    return 'csv'


def is_xml(f, mime):
    if not mime.startswith(("application/xml", "'XML document text",
                            'text/xml')):
        return

    first = f.readline()
    second = f.readline().rstrip(b"\n")
    last = f.readlines()[-1].rstrip(b"\n")

    if not first.startswith(b"<?xml "):
        return

    if second.startswith(b"<rss ") and last.endswith(b"</rss>"):
        return 'rss'

    return 'xml'


def is_json(f, mime):
    if mime == 'application/json':
        return 'json'

    if not is_ascii(f, mime):
        return

    first = f.readline().rstrip(b"\n")
    last = first

    try:
        last = f.readlines()[-1].rstrip(b"\n")
    except Exception as e:
        pass

    if not first.startswith((b"'[{", b"'{")) and not \
            first.startswith((b"[{", b"{")):
        return

    if not last.endswith((b"}]'", b"}'")) and not \
            last.endswith((b"}]", b"}")):
        return

    return 'json'


def is_delimited(f, mime):
    if not is_ascii(f, mime):
        return

    m = OrderedDict([
        ('|', 'pipe'),
        (';', 'semicolon'),
        ("\t", 'tsv'),
        (',', 'csv'),
    ])

    first = f.readline().rstrip(b"\n")

    while first.startswith(b'#'):
        first = f.readline().rstrip(b"\n")

    if isinstance(first, bytes):
        first = first.decode('utf-8')

    second = f.readline().rstrip(b"\n")
    if isinstance(second, bytes):
        second = second.decode('utf-8')

    for d in m:
        c = first.count(d)
        if c == 0:
            continue

        # within 2
        if (c - 2) <= second.count(d) <= (c + 2):
            return m[d]

        if second.count(d) == 0 and first.count(d) > 2:
            return m[d]
