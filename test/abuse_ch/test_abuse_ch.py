
from csirtg_fm import FM
from csirtg_fm.utils.rules import load_rules
from csirtg_fm.content import get_type

rule = 'test/abuse_ch/abuse_ch.yml'
s = FM()


def test_abuse_ch_urlhaus():
    indicators = set()
    tags = set()

    from csirtg_fm.clients.http import Client
    r = load_rules(rule, 'urlhaus')

    cli = Client(rule, 'urlhaus')

    parser_name = get_type(cli.cache)
    assert parser_name == 'csv'

    for i in s.process(rule, 'urlhaus', parser_name, cli, limit=250):
        if not i:
            continue

        indicators.add(i.indicator)
        tags.add(i.tags[0])

    assert 'http://business.imuta.ng/default/us/summit-companies-invoice-12648214' in indicators
    assert 'http://mshcoop.com/download/en/scan' in indicators
    assert 'exploit' in tags
