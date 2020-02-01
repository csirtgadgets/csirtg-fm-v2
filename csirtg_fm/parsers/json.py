import json
from csirtg_fm.parsers import Parser
import logging
import os
from collections import OrderedDict

from csirtg_fm.utils.columns import get_indicator

logger = logging.getLogger(__name__)
TRACE = os.getenv('CSIRTG_FM_PARSER_TRACE', '1')

if logger.getEffectiveLevel() == logging.DEBUG:
    if TRACE == '0':
        logger.setLevel(logging.INFO)


class Json(Parser):

    def __init__(self, *args, **kwargs):
        super(Json, self).__init__(*args, **kwargs)

    def process(self, **kwargs):
        map = self.rule['feeds'][self.feed].get('map')
        values = self.rule['feeds'][self.feed].get('values')
        envelope = self.rule['feeds'][self.feed].get('envelope')

        count = 0
        cache = open(self.cache, 'rb')
        for l in cache.readlines():
            l = l.decode('utf-8')

            try:
                l = json.loads(l, object_pairs_hook=OrderedDict)  # py < 3.6
            except ValueError as e:
                logger.error('json parsing error: {}'.format(e))
                continue

            if envelope:
                l = l[envelope]

            for e in l:
                m = [e[ii] for ii in e]
                i = get_indicator(m)
                self.set_defaults(i)

                if map:
                    for x, c in enumerate(map):
                        #i[values[x]] = e[c]
                        setattr(i, values[x], e[c])

                logger.debug(i)

                yield i.__dict__()

                count += 1

                if self.limit and int(self.limit) == count:
                    break

        cache.close()


Plugin = Json
