#!/usr/bin/env python3

import logging
import os.path
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from pprint import pprint
import sys
import select
import arrow
from time import sleep
import tornado.ioloop as ioloop
from random import randint
from multiprocessing import Process

from csirtg_indicator.format import FORMATS
from csirtg_indicator.constants import COLUMNS

from csirtg_fm.constants import FM_RULES_PATH, CACHE_PATH, LOGLEVEL
from csirtg_fm.utils import setup_logging, get_argument_parser, \
    setup_signals
from csirtg_fm.content import get_type
from csirtg_fm import FM
from csirtg_fm.utils.rules import load_rules
from csirtg_fm.archiver import Archiver, NOOPArchiver

FORMAT = os.getenv('CSIRTG_FM_FORMAT', 'table')
STDOUT_FIELDS = COLUMNS
ARCHIVE_PATH = os.environ.get('CSIRTG_SMRT_ARCHIVE_PATH', CACHE_PATH)
ARCHIVE_PATH = os.path.join(ARCHIVE_PATH, 'fm.db')
GOBACK_DAYS = 3
SERVICE_INTERVAL = os.getenv('CSIRTG_FM_SERVICE_INTERVAL', 60)
LIMIT = os.getenv('CSIRTG_FM_LIMIT', 25)
DELAY = os.getenv('CSIRTG_FM_DELAY', randint(5, 55))
DELAY = int(DELAY)
LIMIT = int(LIMIT)

logger = logging.getLogger(__name__)
logger.setLevel(LOGLEVEL)
logging.getLogger('asyncio').setLevel(logging.WARNING)


def fetch_csirtg(f, limit=250):
    from csirtg_fm.clients.csirtg import Client
    cli = Client()
    user, feed = f.split('/')
    return cli.fetch(user, feed, limit=limit)


def fetch_apwg(f, limit):
    from csirtg_fm.clients.apwg import Client as apwgcli
    cli = apwgcli()
    f = f.split('/')[1]
    indicators = []
    for i in cli.indicators(feed=f, limit=limit, no_last_run=True):
        try:
            # i.geo_resolve()
            i = i.__dict__()

        except Exception as e:
            logger.error(e, exc_info=True)
            continue

        indicators.append(i)

    return indicators


def _run_fm(args, **kwargs):
    data = kwargs.get('data')

    verify_ssl = True
    if args.no_verify_ssl:
        verify_ssl = False

    archiver = NOOPArchiver()
    if args.remember:
        archiver = Archiver(dbfile=args.remember_path)

    goback = args.goback
    if goback:
        goback = arrow.utcnow().shift(days=-int(goback))

    logger.info('starting run...')

    s = FM(archiver=archiver, client=args.client, goback=goback,
           skip_invalid=args.skip_invalid)

    fetch = True
    if args.no_fetch:
        fetch = False

    data = []
    indicators = []

    for r, f, ff in load_rules(args.rule, feed=args.feed):
        if not f:
            print("\n")
            print('Feed not found: %s' % args.feed)
            print("\n")
            raise SystemExit

        # detect which client we should be using

        if '/' in f:
            data = []

            if 'csirtgadgets' in f:
                parser_name = 'csirtg'
                cli = None
                if not os.getenv('CSIRTG_TOKEN'):
                    logger.info('')
                    logger.info('CSIRTG_TOKEN var not set in ENV, skipping %s' % f)
                    logger.info('Sign up for a Free account: https://csirtg.io')
                    logger.info('')
                    continue

                limit = int(args.limit)
                if limit > 500:
                    limit = 500

                if r.get('limit') and int(r['limit']) < limit:
                    limit = int(r['limit'])

                try:
                    for i in fetch_csirtg(f, limit=limit):
                        data.append(i)

                except Exception as e:
                    logger.error(e)
                    continue

            elif 'apwg' in f:
                parser_name = 'apwg'
                cli = None

                limit = int(args.limit)
                if limit > 500:
                    limit = 500

                if r.get('limit') and int(r['limit']) < limit:
                    limit = int(r['limit'])

                try:
                    for i in fetch_apwg(f, limit=limit):
                        data.append(i)

                except Exception as e:
                    logger.error(e, exc_info=True)
                    continue

        else:
            from .clients.http import Client
            cli = Client(r, f, verify_ssl=verify_ssl)

            logger.info(f"processing: {ff} - {f}")
            # fetch the feeds

            try:
                cli.fetch(fetch=fetch)

            except Exception as e:
                logger.error(e, exc_info=True)
                continue

            # decode the content and load the parser
            try:
                logger.debug('testing parser: %s' % cli.cache)
                parser_name = get_type(cli.cache)
                logger.debug('detected parser: %s' % parser_name)

            except Exception as e:
                logger.debug(e)

            if r['feeds'][f].get('pattern'):
                logger.debug("overriding parser with pattern..")
                parser_name = 'pattern'

            if not parser_name:
                parser_name = r['feeds'][f].get('parser') or r.get('parser') \
                              or 'pattern'

        try:
            for i in s.process(r, f, parser_name, cli, limit=args.limit,
                               indicators=data):
                if not i:
                    continue

                indicators.append(i)

        except Exception as e:
            logger.error(e)
            import traceback
            traceback.print_exc()

    if args.client == 'stdout':
        for l in FORMATS[args.format](data=indicators,
                                      cols=args.fields.split(',')):
            print(l)

    logger.info('cleaning up')
    count = archiver.cleanup()
    logger.info('purged %i records' % count)
    archiver.clear_memcache()

    logger.info('finished run')
    if args.service:
        logger.info('sleeping...')


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        Env Variables:
            CSIRTG_RUNTIME_PATH


        example usage:
            $ csirtg-fm -r rules/default
            $ csirtg-fm -r csirtg.yml --feed csirtgadgets/darknet
            $ CIF_TOKEN=1234 csirtg-fm -r csirtg.yml --client cif -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='csirtg-fm',
        parents=[p],
    )

    p.add_argument("-r", "--rule",
                   help="specify the rules directory or specific rules file "
                        "[default: %(default)s",
                   default=FM_RULES_PATH)

    p.add_argument("-f", "--feed", help="specify the feed to process")

    p.add_argument("--limit", help="limit the number of records processed "
                                   "[default: %(default)s]",
                   default=25)

    p.add_argument('--no-fetch', help='do not re-fetch if the cache exists',
                   action='store_true')
    p.add_argument('--no-verify-ssl', help='turn TLS/SSL verification OFF',
                   action='store_true')

    p.add_argument('--skip-invalid', help="skip invalid indicators in "
                                          "DEBUG (-d) mode",
                   action="store_true")
    p.add_argument('--skip-broken', help='skip seemingly broken feeds',
                   action='store_true')

    p.add_argument('--format', help='specify output format '
                                    '[default: %(default)s]"', default=FORMAT,
                   choices=FORMATS)
    p.add_argument('--fields', help='specify fields for stdout '
                                    '[default %(default)s]"',
                   default=','.join(STDOUT_FIELDS))

    p.add_argument('--remember-path', help='specify remember db path '
                                           '[default: %(default)s',
                   default=ARCHIVE_PATH)
    p.add_argument('--remember', help='remember what has been already '
                                      'processed', action='store_true')

    p.add_argument('--client', default='stdout')

    p.add_argument('--goback', help='specify default number of days to start '
                                    'out at [default %(default)s]',
                   default=GOBACK_DAYS)

    p.add_argument('--service', action='store_true',
                   help="start in service mode")

    p.add_argument('--service-interval', help='set run interval '
                                              '[minutes, default %(default)s]',
                   default=SERVICE_INTERVAL)

    p.add_argument('--delay', help='specify initial delay', default=DELAY)

    args = p.parse_args()

    setup_logging(args)

    if args.verbose:
        logger.setLevel('INFO')

    if args.debug:
        logger.setLevel('DEBUG')

    if not args.service:
        data = None
        if select.select([sys.stdin, ], [], [], 0.0)[0]:
            data = sys.stdin.read()
        try:
            _run_fm(**{
                'args': args,
                'data': data,
            })
        except KeyboardInterrupt:
            logger.info('exiting..')

        except Exception as e:
            logger.error(e)
            if logger.getEffectiveLevel() == logging.DEBUG:
                import traceback
                traceback.print_exc()

        raise SystemExit

    # we're running as a service
    setup_signals(__name__)
    service_interval = int(args.service_interval)
    r = float(args.delay)

    if r > 0:
        logger.info(f"random delay is {r}")
        logger.info(f"running every {service_interval} after that")
        try:
            sleep((r * 60))

        except KeyboardInterrupt:
            logger.info('shutting down')
            raise SystemExit

        except Exception as e:
            logger.error(e)
            raise SystemExit

    # we run the service as a fork, a cleaner way to give back any memory
    # consumed by large feed processing
    def _run_fork():
        logger.debug('forking process...')
        p = Process(target=_run_fm, args=(args,))
        p.daemon = False
        p.start()
        p.join()

    # first run, PeriodicCallback has builtin wait..
    _run_fork()

    main_loop = ioloop.IOLoop()
    service_interval = (service_interval * 10000)
    loop = ioloop.PeriodicCallback(_run_fork, service_interval)

    try:
        loop.start()
        main_loop.start()

    except KeyboardInterrupt:
        logger.info('exiting..')

    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    main()
