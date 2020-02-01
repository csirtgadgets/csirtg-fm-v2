from csirtg_dt import get as get_ts
from csirtg_indicator.utils import resolve_itype
from csirtg_indicator import Indicator
import re

from collections import OrderedDict


def _calc_timestamps(i, timestamps):
    timestamps = sorted(timestamps, reverse=True)

    if len(timestamps) > 0:
        i.last_at = timestamps[0]

    if len(timestamps) > 1:
        i.first_at = timestamps[1]


def _calc_ports(i, ports):
    if len(ports) == 0:
        return

    if len(ports) == 1:
        i.portlist = ports[0]
        return

    if ports[0] > ports[1]:
        i.portlist = ports[0]
        i.dest_portlist = ports[1]
        return

    i.portlist = ports[1]
    i.dest_portlist = ports[0]


def _get_indicator(i):
    i2 = Indicator()
    timestamps = []
    ports = []

    # prioritize the various elements..
    for e in i:
        if i[e] == 'CC':
            i2.cc = e
            continue

        if i[e] == 'indicator':
            if i2.indicator:
                i2.reference = e
            else:
                i2.indicator = e
            continue

        if i[e] == 'timestamp':
            timestamps.append(get_ts(e))
            continue

        if i[e] == 'float':
            i2.asn = e
            continue

        if i[e] == 'int':
            ports.append(e)
            continue

        if i[e] == 'description':
            i2.description = e
            continue

        if i[e] == 'string':
            if re.match(r'[0-9A-Za-z\.\s\/]+', e) and i2.asn:
                i2.asn_desc = e
                continue

            if 4 <= len(e) <= 10 and re.match('[a-z-A-Z]+,?', e) \
                    and e not in ['ipv4', 'fqdn', 'url', 'ipv6']:
                i2.tags = [e]
                continue

            if ' ' in e and 5 <= len(e) and not i2.asn_desc:
                i2.description = e
                continue

    _calc_timestamps(i2, timestamps)
    _calc_ports(i2, ports)
    return i2


def _get_elements(l, hints):
    i = OrderedDict()

    for e in l:
        if not isinstance(e, (str, bytes)):
            continue

        e = e.rstrip()
        e = e.lstrip()

        if re.match('^[a-zA-Z]{2}$', e):
            i[e] = 'CC'
            continue

        t = None
        try:
            t = resolve_itype(e.rstrip('/'))
            # 25553.0 ASN formats trip up FQDN resolve itype
            if t and not (t == 'fqdn' and re.match('^\d+\.[0-9]$', e)):
                i[e] = 'indicator'
                continue

        except Exception:
            pass

        # integers
        if isinstance(e, int):
            i[e] = 'int'
            continue

        # floats
        if isinstance(e, float) or re.match('^\d+\.[0-9]$', e):
            i[e] = 'float'
            continue

        # timestamps
        try:
            parse_timestamp(e)
            i[e] = 'timestamp'
            continue
        except Exception:
            pass

        # basestrings
        if isinstance(e, (str, bytes)):
            if hints:
                for ii in range(0, 25):
                    if len(hints) == ii:
                        break

                    if e.lower() == hints[ii].lower():
                        i[e] = 'description'
                        break

            if not i.get(e):
                i[e] = 'string'

    return i


def get_indicator(l, hints=None):
    if not isinstance(l, list):
        l = [l]

    l[-1] = l[-1].rstrip("\n")
    i = _get_elements(l, hints)
    i2 = _get_indicator(i)

    return i2


def main():
    i = ['192.168.1.1', '2015-02-28T00:00:00Z', 'scanner',
         '2015-02-28T01:00:00Z', 1159, 2293]

    i2 = get_indicator(i)
    print(i2)


if __name__ == "__main__":
    main()
