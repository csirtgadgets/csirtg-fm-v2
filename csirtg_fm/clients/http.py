import logging
import os
from datetime import datetime
import re
from time import sleep
import arrow
import requests

from csirtg_fm.constants import VERSION, FM_CACHE, RE_CACHE_TYPES, RE_FQDN
from csirtg_fm.clients.constants import FETCHER_TIMEOUT, RETRIES, \
    RETRIES_DELAY, NO_HEAD, TRACE

from csirtg_fm.utils import get_modified, get_size, decode

logging.getLogger('requests.packages.urllib3.connectionpool')\
    .setLevel(logging.WARNING)

if TRACE:
    logging.getLogger("requests.packages.urllib3.connectionpool")\
        .setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


class Client(object):

    username = None
    password = None
    auth = False

    def __init__(self, rule, feed, **kwargs):

        self.feed = feed
        self.rule = rule
        self.cache = kwargs.get('cache', FM_CACHE)
        self.timeout = FETCHER_TIMEOUT
        self.verify_ssl = kwargs.get('verify_ssl', True)

        self.handle = requests.session()
        self.handle.headers['User-Agent'] = \
            f"csirtg-fm/{VERSION} (csirtgadgets.com)"

        self.handle.headers['Accept'] = 'application/json'

        if isinstance(self.rule, str):
            from csirtg_fm.utils.rules import load_rules
            self.rule, f, p = next(load_rules(self.rule, feed))

        if not self.rule.get('defaults'):
            self.rule['defaults'] = {}

        self.provider = self.rule.get('provider')

        self._init_remote(feed)
        self._init_provider()
        self._init_paths(feed)

        if self.username:
            self.auth = (self.username, self.password)

    def _init_remote(self, feed):
        if self.rule.get('remote'):
            self.remote = self.rule['remote']

        elif self.rule.get('defaults') and self.rule['defaults'].get('remote'):
            self.remote = self.rule['defaults']['remote']

        else:
            self.remote = self.rule['feeds'][feed].get('remote')

        if self.remote and '{token}' in self.remote:
            if self.rule['token']:
                if self.rule['token'].endswith('_TOKEN'):
                    self.rule['token'] = os.getenv(self.rule['token'])
                self.remote = self.remote.format(token=self.rule['token'])
            else:
                self.remote = self.remote.format(token='')

        elif self.rule.get('token'):
            header = 'Authorization: Token token='
            if self.rule.get('token_header'):
                header = self.rule['token_header']

            self.token = f"{header}{self.rule['token']}"

    def _init_provider(self):
        if self.provider:
            return

        if self.rule['defaults'].get('provider'):
            self.provider = self.rule['defaults']['provider']
            return

        match = re.search(RE_FQDN, self.remote)
        try:
            self.provider = match[0]
        except TypeError:
            self.provider = match.group(0)

        try:
            self.rule['defaults']['provider'] = match[0]
        except TypeError:
            self.rule['defaults']['provider'] = match.group(0)

    def _init_paths(self, feed):
        if os.path.isfile(self.remote):
            self.cache = self.remote
            return

        self.dir = os.path.join(self.cache, self.provider)
        logger.debug(self.dir)

        if not os.path.exists(self.dir):
            try:
                os.makedirs(self.dir)
            except OSError:
                logger.critical('failed to create {0}'.format(self.dir))
                raise

        if self.rule['feeds'][feed].get('cache'):
            self.cache = os.path.join(self.dir,
                                      self.rule['feeds'][feed]['cache'])
            self.cache_file = True

        elif self.remote and RE_CACHE_TYPES.search(self.remote):
            self.cache = RE_CACHE_TYPES.search(self.remote).groups()
            self.cache = os.path.join(self.dir, self.cache[0])
            self.cache_file = True

        else:
            self.cache = os.path.join(self.dir, self.feed)

        # test to see if we've decompressed a similarly named text file
        logger.debug(self.cache)
        if self.cache.endswith('.zip'):
            _, f = os.path.split(self.cache)
            f, t = f.rsplit('.', 1)
            f = '%s.txt' % f  # match csv
            f = os.path.join(_, f)
            if os.path.exists(f):
                self.cache = f

            # csv
            _, f = os.path.split(self.cache)
            f, t = f.rsplit('.', 1)
            f = '%s' % f
            f = os.path.join(_, f)
            if os.path.exists(f):
                self.cache = f

        logger.debug('CACHE %s' % self.cache)

    def _cache_refresh(self, s):
        resp = s.get(self.remote, stream=True, auth=self.auth,
                     timeout=self.timeout, verify=self.verify_ssl)

        if resp.status_code == 200:
            return resp

        if resp.status_code not in [429, 500, 502, 503, 504]:
            return

        n = RETRIES
        retry_delay = RETRIES_DELAY
        while True:
            if resp.status_code == 429:
                logger.info('Rate Limit Exceeded'
                            'retrying in %ss' % retry_delay)
            else:
                logger.error('%s found, retrying in %ss' %
                             (resp.status_code, retry_delay))

            sleep(retry_delay)
            resp = s.get(self.remote, stream=True, auth=self.auth,
                         timeout=self.timeout,
                         verify=self.verify_ssl)

            if resp.status_code == 200:
                return resp

            n -= 1
            if n == 0:
                break

    def _cache_write(self, s):
        resp = self._cache_refresh(s)

        if not resp:
            return

        with open(self.cache, 'wb') as f:
            for block in resp.iter_content(1024):
                f.write(block)

        self.cache = decode(self.cache)

    def _fetch(self, fetch):
        if get_size(self.cache) == 0:
            self._cache_write(self.handle)
            self.cache = decode(self.cache)
            return

        if not fetch and os.path.exists(self.cache):
            self.cache = decode(self.cache)
            return

        # raise
        if arrow.utcnow().shift(minutes=-5) < get_modified(self.cache):
            self.cache = decode(self.cache)
            return

        return True

    def fetch(self, fetch=True):
        if not self._fetch(fetch):
            return

        try:
            resp = self.handle.head(self.remote, auth=self.auth,
                                    verify=self.verify_ssl)

        except Exception as e:
            logger.error(f"connection error: {self.remote}")
            logger.debug(e)
            return

        if resp.status_code in [429, 500, 502, 503, 504]:
            logger.info('HEAD check received: %s' % str(resp.status_code))
            logger.info('skipping until next cycle..')
            self.cache = decode(self.cache)
            return

        if not resp.headers.get('Last-Modified'):
            self._cache_write(self.handle)
            return

        ts = resp.headers.get('Last-Modified')

        ts1 = arrow.get(datetime.strptime(ts, '%a, %d %b %Y %X %Z'))
        ts2 = get_modified(self.cache)

        if not NO_HEAD and (ts1 <= ts2):
            self.cache = decode(self.cache)
            return

        self._cache_write(self.handle)
