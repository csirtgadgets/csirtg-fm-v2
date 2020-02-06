
import os
import yaml
import logging

logger = logging.getLogger(__name__)


def _load_rules_dir(path):
    for f in sorted(os.listdir(path)):
        if f.startswith('.'):
            continue

        if os.path.isdir(f):
            continue

        if not f.endswith(".yml"):
            continue

        with open(os.path.join(path, f)) as FILE:
            r = yaml.safe_load(FILE)

        for feed in r['feeds']:
            yield r, feed, f


def load_rules(rule, feed=None):
    if os.path.isdir(rule):
        for r, feed, f in _load_rules_dir(rule):
            yield r, feed, f

    else:
        path = rule
        if os.path.isfile(rule):
            with open(rule) as F:
                rule = yaml.safe_load(F)

        if feed:
            from pprint import pprint
            pprint(rule)
            try:
                rule['feeds'] = {feed: rule['feeds'][feed]}
            except Exception as e:

                logger.debug(e, exc_info=True)
                return None

        for f in rule['feeds']:
            yield rule, f, path
