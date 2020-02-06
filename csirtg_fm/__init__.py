#!/usr/bin/env python3

import logging
import os.path
import itertools

from csirtg_indicator.utils import resolve_itype
from csirtg_indicator.constants import COLUMNS
from csirtg_indicator import Indicator

from csirtg_fm.constants import CACHE_PATH
from csirtg_fm.utils import load_plugin, \
    chunk
from csirtg_fm.constants import FIREBALL_SIZE

from csirtg_fm.utils.rules import load_rules
from csirtg_fm.utils.indicator import format_keys
from csirtg_fm.archiver import NOOPArchiver

FORMAT = os.getenv('CSIRTG_FM_FORMAT', 'table')
STDOUT_FIELDS = COLUMNS
ARCHIVE_PATH = os.environ.get('CSIRTG_SMRT_ARCHIVE_PATH', CACHE_PATH)
ARCHIVE_PATH = os.path.join(ARCHIVE_PATH, 'fm.db')

# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Factory.html
# https://gist.github.com/pazdera/1099559
logging.getLogger("requests").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class FM(object):

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.__exit__()

    def __init__(self, **kwargs):
        self.archiver = kwargs.get('archiver', NOOPArchiver())
        self.goback = kwargs.get('goback')
        self.skip_invalid = kwargs.get('skip_invalid')
        self.client = kwargs.get('client')

        if self.client and self.client != 'stdout':
            self._init_client()

        if logger.getEffectiveLevel() != logging.DEBUG:
            self.skip_invalid = True

    def _init_client(self):
        if self.client == 'stdout':
            return

        plugin_path = os.path.join(os.path.dirname(__file__), 'clients')
        self.client = load_plugin(plugin_path, self.client)
        if not self.client:
            raise ImportError(f"Unable to load plugin: {self.client}")

        self.client = self.client.Plugin()

    def is_valid(self, i):
        try:
            resolve_itype(i['indicator'])
        except TypeError as e:
            if logger.getEffectiveLevel() == logging.DEBUG:
                if not self.skip_invalid:
                    raise e
            return False

        return True

    def is_old(self, i):
        if i.last_at and i.last_at < self.goback:
            return True

    def is_archived(self, i):
        if isinstance(self.archiver, NOOPArchiver):
            return

        if self.archiver.search(i):
            logger.debug(f"skipping: {i.indicator}/{i.provider}/"
                         f"{i.first_at}/{i.last_at}")
            return True

        logger.debug(f"adding: {i.indicator}/{i.provider}/"
                     f"{i.first_at}/{i.last_at}")

    def process(self, rule, feed, parser_name, cli, limit=None, indicators=[]):

        if isinstance(rule, str):
            rule, _, _ = next(load_rules(rule, feed))

        if rule['feeds'][feed].get('limit') and limit == 25:
            limit = rule['feeds'][feed].get('limit')

        if parser_name not in ['csirtg', 'apwg']:
            # detect and load the parser
            plugin_path = os.path.join(os.path.dirname(__file__), 'parsers')
            parser = load_plugin(plugin_path, parser_name)
            parser = parser.Plugin(rule=rule, feed=feed, cache=cli.cache,
                                   limit=limit)

            # bring up the pipeline
            indicators = parser.process(skip_invalid=self.skip_invalid)

        indicators = (i for i in indicators if self.is_valid(i))
        indicators = (Indicator(**i) for i in indicators)
        indicators = (format_keys(i) for i in indicators)

        # check to see if the indicator is too old
        if self.goback:
            indicators = (i for i in indicators if not self.is_old(i))

        if limit:
            indicators = itertools.islice(indicators, int(limit))

        indicators = (i for i in indicators if not self.is_archived(i))

        indicators_batches = chunk(indicators, int(FIREBALL_SIZE))
        for batch in indicators_batches:
            # send batch
            if self.client and self.client != 'stdout':
                logger.info('sending: %i' % len(batch))
                self.client.indicators_create(batch)

            # archive
            self.archiver.begin()
            for i in batch:
                yield i
                self.archiver.create(i)

            # commit
            self.archiver.commit()
