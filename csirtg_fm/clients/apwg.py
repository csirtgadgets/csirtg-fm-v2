#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import os.path
import os
from datetime import datetime, timedelta
from pprint import pprint
import json
import requests
from csirtg_indicator import Indicator
from csirtg_indicator.format import FORMATS

VERSION = '3.0a0'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'
LIMIT = 10000000
APWG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
REMOTE_DEFAULT = 'example.api.apwg.org'
REMOTE = os.getenv('APWG_REMOTE', REMOTE_DEFAULT)
TOKEN = os.environ.get('APWG_TOKEN')
LAST_RUN_CACHE = os.environ.get('APWG_LAST_RUN_CACHE', '/tmp/.apwg_last_run')
CONFIDENCE_DEFAULT = os.getenv('APWG_CREATE_CONFIDENCE', 50)
GROUP = os.getenv('APWG_GROUP')

logger = logging.getLogger(__name__)


class Client(object):

    def __init__(self, token=TOKEN, proxy=None, timeout=300,
                 lastrun=LAST_RUN_CACHE, **kwargs):

        self.proxy = proxy
        self.remote = REMOTE
        self.timeout = timeout
        self.token = token
        self.group = kwargs.get('group', GROUP)
        self.last_run_file = lastrun
        self.hours = kwargs.get('hours', 24)

        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'apwgsdk-py/{}'.format(VERSION)
        self.session.headers['Content-Type'] = 'application/json'

        if self.group:
            self.remote = '{}/groups/{}'.format(self.remote, self.group)

        if not os.path.isdir(self.last_run_file):
            os.makedirs(self.last_run_file)

    def _get(self, uri, params={}):
        if not uri.startswith('http'):
            uri = self.remote + uri

        body = self.session.get(uri, params=params, verify=True,
                                timeout=self.timeout)

        if body.status_code == 200:
            return json.loads(body.text)

        if body.status_code == 401:
            raise RuntimeError('unauthorized')

    def _post(self, uri, data):
        if not uri.startswith('http'):
            uri = self.remote + uri

        resp = self.session.post(uri, data=data, timeout=self.timeout)

        if resp.status_code == 201:
            return json.loads(resp.text)

        if resp.status_code == 401:
            raise RuntimeError('unauthorized')

        raise RuntimeError(resp.text)

    def _last_run(self):
        end = datetime.utcnow()
        hours = self.hours
        lastrun = os.path.join(self.last_run_file, "lastrun")

        if os.path.exists(lastrun):
            with open(lastrun) as f:
                start = f.read().strip("\n")
                start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S.%f')
        else:
            hours = int(hours)
            start = end - timedelta(hours=hours, seconds=-1)

        logger.info("start:{0}".format(start))
        logger.info("end:{0}".format(end))

        return start, end

    def _update_last_run(self, no_last_run=False):
        if no_last_run:
            return

        start, end = self._last_run()

        with open(os.path.join(self.last_run_file, "lastrun"), "w") as f:
            f.write(str(end))

    def indicators(self, feed='phish', limit=500, no_last_run=False,
                   confidence=4):
        start, end = self._last_run()
        if isinstance(limit, str):
            limit = int(limit)

        uri = "{}/{}?t={}&dd_date_start={}&dd_date_end={}&confidence_low=90" \
            .format(
            self.remote,
            feed,
            self.token,
            start.strftime('%s'),
            end.strftime('%s'),
        )

        body = self._get(uri)
        tags = "phishing"

        if feed == 'mal_ip':
            feed = 'mal_ips'
            tags = 'scanner'

        for i in body['_embedded'][feed]:
            indicator = None
            rdata = None
            if i.get('url'):
                i["url"] = i["url"].lstrip()
                indicator = i['url']
                rdata = i.get('ip')
                del i['ip']

            if i.get('ip'):
                indicator = i['ip']

            try:
                yield Indicator(**{
                    "indicator": indicator,
                    "last_at": datetime.fromtimestamp(i['date_discovered'])
                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "description": i["brand"],
                    "confidence": confidence,
                    "provider": "apwg.org",
                    "tlp": "amber",
                    'rdata': rdata,
                    "tags": tags
                })

            except Exception as e:
                logger.error(e)
                continue

            if limit is not None:
                limit -= 1
                if limit == 0:
                    break

        self._update_last_run(no_last_run=no_last_run)

    def indicators_create(self, indicator=None, confidence=None,
                          description=None, lasttime=datetime.utcnow()):
        if isinstance(lasttime, str):
            lasttime = datetime.fromtimestamp(lasttime) \
                .strftime("%Y-%m-%dT%H:%M:%SZ")

        # normalize the url
        i = Indicator(**{
            "indicator": indicator,
            "last_at": lasttime,
            "description": description,
            "confidence": int(confidence),
        })
        lasttime = int((i.lasttime - datetime(1970, 1, 1)).total_seconds())
        u = {
            'url': i.indicator,
            'date_discovered': lasttime,
            'confidence_level': int(i.confidence),
        }

        if i.description:
            u['brand'] = i.description

        uri = self.remote + '?t=%s' % self.token
        data = json.dumps(u)
        return self._post(uri, data)


def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ export APWG_REMOTE=https://example.api.apwg.org # see relvant doc for api info
            $ export APWG_TOKEN=123412341234
            $ apwg -v

            $ apwg --indicator-create http://badguy.com/1.html --description paypal
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='apwg'
    )

    p.add_argument('-d', '--debug', dest='debug', action="store_true")

    p.add_argument('--remote',
                   help="specify the remote uri [default %(default)s]",
                   default=REMOTE)
    p.add_argument("--token", dest="token",
                   help="specify token [default %(default)s]", default=TOKEN)

    p.add_argument("--limit", dest="limit",
                   help="limit the number of records processed", default=500)
    p.add_argument("--last-run-cache", default=LAST_RUN_CACHE)
    p.add_argument("--past-hours",
                   help="number of hours to go back and retrieve", default=24)

    p.add_argument("--no-last-run", help="do not modify lastrun file",
                   action="store_true")

    p.add_argument('--indicator-create',
                   help="specify an indicator to be created")
    p.add_argument('-c', '--confidence',
                   help="specify confidence level of indicator [default %(default)s",
                   default=CONFIDENCE_DEFAULT)
    p.add_argument('--description', help='description of indicator')
    p.add_argument('--last_at',
                   help='last time indicator was observed '
                        '[default %s(default)s]',
                   default=datetime.utcnow())

    p.add_argument('--group')

    args = p.parse_args()

    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)

    if args.remote == REMOTE_DEFAULT:
        print("\nThe correct API REMOTE URI needs to be supplied\n"
              "Contact support@ecrimex.net for more information.\n")
        raise SystemExit

    if args.indicator_create:
        cli = Client()
        try:
            r = cli.indicators_create(indicator=args.indicator_create,
                                      confidence=args.confidence,
                                      description=args.description,
                                      lasttime=args.lasttime)
            logger.info('indicator created successfully: {}'.format(r['id']))
            if args.debug:
                pprint(r)

        except Exception as e:
            logger.debug(e)
            logger.error('error creating indicator')

        raise SystemExit

    cli = Client(hours=args.past_hours)

    indicators = cli.indicators(no_last_run=args.no_last_run, limit=args.limit)
    cols = ['last_at',
            'indicator',
            'confidence',
            'description']

    for l in FORMATS['table'](data=sorted(indicators,
                                          key=lambda i: i['reported_at']),
                              cols=cols):
        print(l)


if __name__ == "__main__":
    main()
