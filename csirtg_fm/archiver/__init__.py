try:
    import sqlalchemy
except ImportError:
    raise ImportError('Requires sqlalchemy')

import logging
import os
import arrow

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine, asc, event
from sqlalchemy.orm import sessionmaker, scoped_session, load_only
from csirtg_fm.archiver.constants import TRACE, CACHE_SIZE, CLEANUP_DAYS, \
    SYNC, DB_FILE

from pprint import pprint

from .noop import NOOPArchiver

# this needs to be done first..
from csirtg_fm.archiver.constants import BASE
from .indicator import Indicator

logger = logging.getLogger(__name__)

logger.setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(logging.ERROR)

if not TRACE:
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode = MEMORY")
    cursor.execute("PRAGMA synchronous = {}".format(SYNC))
    cursor.execute("PRAGMA temp_store = MEMORY")
    cursor.execute("PRAGMA cache_size = {}".format(CACHE_SIZE))
    cursor.execute("PRAGMA auto_vacuum = INCREMENTAL")
    cursor.close()


# http://www.pythoncentral.io/sqlalchemy-orm-examples/
class Archiver(object):
    def __init__(self, dbfile=DB_FILE, autocommit=False, dictrows=True,
                 **kwargs):

        self.dbfile = dbfile
        self.autocommit = autocommit
        self.dictrows = dictrows
        self.path = "sqlite:///{0}".format(self.dbfile)

        echo = False
        if TRACE:
            echo = True

        # http://docs.sqlalchemy.org/en/latest/orm/contextual.html
        self.engine = create_engine(self.path, echo=echo)
        self.handle = sessionmaker(bind=self.engine)
        self.handle = scoped_session(self.handle)
        self._session = None
        self._tx_count = 0

        BASE.metadata.create_all(self.engine)
        logger.debug('database path: {}'.format(self.path))

        self.clear_memcache()

    def begin(self):
        self._tx_count += 1
        if self._session:
            return self._session

        self._session = self.handle()
        return self._session

    def commit(self):
        if self._tx_count == 0:
            raise Exception("commit outside of transaction")
        self._tx_count -= 1
        if self._tx_count == 0:
            self._session.commit()
            self._session = None

    def clear_memcache(self):
        self.memcache = {}
        self.memcached_provider = None

    def cache_provider(self, provider):
        if self.memcached_provider == provider:
            return

        self.memcached_provider = provider
        self.memcache = {}
        logger.info("Caching archived indicators for provider {}".
                    format(provider))
        q = self.handle().query(Indicator) \
            .filter_by(provider=provider) \
            .order_by(asc(Indicator.last_at), asc(Indicator.first_at),
                      asc(Indicator.created_at))

        q = q.options(load_only("indicator", "group", "tags", "first_at",
                                "last_at"))
        q = q.yield_per(1000)
        for i in q:
            self.memcache[i.indicator] = (i.group, i.tags, i.first_at,
                                          i.last_at)

        logger.info("Cached provider {} in memory, {} objects".
                    format(provider, len(self.memcache)))

    def search(self, indicator):
        tags = indicator.tags
        if isinstance(tags, list):
            tags.sort()
            tags = ','.join(tags)

        self.cache_provider(indicator.provider)

        # Is there any cached record?
        if indicator.indicator not in self.memcache:
            return False

        (ex_group, ex_tags, ex_ft, ex_lt) = self.memcache[indicator.indicator]

        # Is the indicator or tags different?
        if (ex_group, ex_tags) != (indicator.group, tags):
            return False

        timestamp_comparisons = (
            (ex_ft, indicator.first_at),
            (ex_lt, indicator.last_at),
        )

        for existing_ts, indicator_ts in timestamp_comparisons:
            # If the new indicator does not have this ts, ignore it
            if indicator_ts is None:
                continue
            # Cache has no old ts, but there is a new one, we are out of date
            if existing_ts is None:
                return False
            # otherwise, compare timestamps to see if we are out of date
            if indicator_ts.replace(tzinfo=None) > \
                    existing_ts.replace(tzinfo=None):
                return False

        # If we made it here, the cached indicator is >= to the one in the
        # feed.
        return True

    def create(self, indicator):
        tags = indicator.tags
        if isinstance(indicator.tags, list):
            indicator.tags.sort()
            tags = ','.join(indicator.tags)

        i = indicator.indicator

        i = Indicator(indicator=i, provider=indicator.provider,
                      group=indicator.group, last_at=indicator.last_at,
                      tags=tags, first_at=indicator.first_at)

        s = self.begin()
        s.add(i)
        s.commit()

        first_at = None
        if indicator.first_at:
            first_at = indicator.first_at.replace(tzinfo=None)

        last_at = None
        if indicator.last_at:
            last_at = indicator.last_at.replace(tzinfo=None)

        self.memcache[indicator.indicator] = (
            indicator.group,
            tags,
            first_at,
            last_at
        )

        return i.id

    def cleanup(self, days=CLEANUP_DAYS):
        days = int(days)
        date = arrow.utcnow()
        date = date.shift(days=-days)

        s = self.begin()
        count = s. \
            query(Indicator).filter(Indicator.created_at < date.datetime) \
            .delete()
        self.commit()

        return count
