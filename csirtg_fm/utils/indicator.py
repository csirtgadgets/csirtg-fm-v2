from csirtg_indicator import Indicator


def format_keys(i):
    d = i.__dict__()
    for k in d:
        if not isinstance(d[k], str):
            continue

        if '{' not in d[k]:
            continue

        try:
            d[k] = d[k].format(**d)
        except (KeyError, ValueError, IndexError):
            pass

    return Indicator(**d)
