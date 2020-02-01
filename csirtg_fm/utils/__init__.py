import logging
from argparse import ArgumentParser
import signal
import os
import importlib
from pprint import pprint
import arrow

from csirtgsdk.constants import LOG_FORMAT
from csirtg_fm.constants import RUNTIME_PATH, VERSION, LOGLEVEL
from csirtg_fm.content import get_mimetype
from .decoders import decompress_gzip, decompress_zip


def get_argument_parser():
    BasicArgs = ArgumentParser(add_help=False)
    BasicArgs.add_argument('-d', '--debug', dest='debug', action="store_true")
    BasicArgs.add_argument('-v', '--verbose', dest='verbose',
                           action="store_true")
    BasicArgs.add_argument('-V', '--version', action='version',
                           version=VERSION)
    BasicArgs.add_argument(
        "--runtime-path",
        help="specify the runtime path [default %(default)s]",
        default=RUNTIME_PATH
    )
    return ArgumentParser(parents=[BasicArgs], add_help=False)


# py3.5+
def load_plugin(path, plugin):
    path = os.path.join(path, ('%s.py' % plugin))
    spec = importlib.util.spec_from_file_location(path, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setup_logging(args):
    loglevel = logging.getLevelName(LOGLEVEL)

    if args.verbose:
        loglevel = logging.INFO

    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)


def setup_signals(name):
    logger = logging.getLogger(__name__)

    def sigterm_handler(_signo, _stack_frame):
        logger.info('SIGTERM Caught for {}, shutting down...'.format(name))
        raise SystemExit

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)


def setup_runtime_path(path):
    if not os.path.isdir(path):
        os.mkdir(path)


def chunk(it, slice=50):
    """Generate sublists from an iterator
    >>> list(chunk(iter(range(10)),11))
    [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]
    >>> list(chunk(iter(range(10)),9))
    [[0, 1, 2, 3, 4, 5, 6, 7, 8], [9]]
    >>> list(chunk(iter(range(10)),5))
    [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]
    >>> list(chunk(iter(range(10)),3))
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    >>> list(chunk(iter(range(10)),1))
    [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9]]
    """

    assert(slice > 0)
    a = []

    for x in it:
        if len(a) >= slice :
            yield a
            a = []
        a.append(x)

    if a:
        yield a


def get_modified(f):
    ts = os.stat(f)
    ts = arrow.get(ts.st_mtime)
    return ts


def get_size(f):
    if not os.path.isfile(f):
        return 0

    s = os.stat(f)
    return s.st_size


def decode(f):
    ftype = get_mimetype(f)

    if 'gzip' in ftype:
        return decompress_gzip(f)

    if 'zip' in ftype:
        for fname in decompress_zip(f):
            return os.path.join(os.path.dirname(f), fname)

    return f
