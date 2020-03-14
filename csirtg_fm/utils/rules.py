
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


def _load_rules(rule, feed=None):
    if os.path.isdir(rule):
        for r, feed, f in _load_rules_dir(rule):
            yield r, feed, f

    else:
        path = rule
        if os.path.isfile(rule):
            with open(rule) as F:
                rule = yaml.safe_load(F)

        if not isinstance(rule, dict):
            raise FileNotFoundError(f"unable to find/load {rule}")

        if feed:
            try:
                rule['feeds'] = {feed: rule['feeds'][feed]}
            except Exception as e:

                logger.debug(e, exc_info=True)
                return None

        for f in rule['feeds']:
            yield rule, f, path


def load_rules(rule, feed=None):
    if ',' in rule:
        for r in rule.split(','):
            yield from _load_rules(r, feed)

    else:
        yield from _load_rules(rule, feed)
