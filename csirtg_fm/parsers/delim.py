
import re
import logging
import os

from csirtg_fm.parsers import Parser
from ..utils.columns import get_indicator
from csirtg_fm.content import peek

logger = logging.getLogger(__name__)
TRACE = os.getenv('CSIRTG_FM_PARSER_TRACE', '1')

if logger.getEffectiveLevel() == logging.DEBUG:
    if TRACE == '0':
        logger.setLevel(logging.INFO)


class Delim(Parser):

    def __init__(self, **kwargs):
        super(Delim, self).__init__(**kwargs)

        if self.delim and isinstance(self.delim, str):
            self.pattern = re.compile(self.delim)

        self.reverse = False
        if self.rule.get('reverse', '') == '1':
            self.reverse = True

    def process(self, **kwargs):
        count = 0

        # TODO- rb
        cache = open(self.cache, 'r', encoding='utf-8', errors='ignore')

        hints = peek(cache, lines=25, delim=self.delim)
        cache.seek(0)
        g = cache.readlines()
        if self.reverse:
            g = reversed(g)

        for l in g:
            if self.ignore(l):  # comment or skip
                continue

            l = l.lstrip()
            l = l.rstrip()

            logger.debug(l)
            m = self.pattern.split(l)

            if hasattr(self, 'strip'):
                for idx, v in enumerate(m):
                    m[idx] = v.strip(self.strip)

            i = get_indicator(m, hints=hints)

            if not i.itype:
                logger.info("unable to detect indicator: \n%s" % l)
                continue

            if self.rule['defaults'].get('values'):
                for idx, v in enumerate(self.rule['defaults']['values']):
                    if v:
                        setattr(i, v, m[idx])

            self.set_defaults(i)

            if self.rule['feeds'][self.feed].get('values'):
                for idx, v in enumerate(self.rule['feeds'][self.feed]['values']):
                    if v:
                        setattr(i, v, m[idx])

            yield i.__dict__()

            logger.debug(i)

            count += 1
            if self.limit == count:
                break

            cache.close()


Plugin = Delim
