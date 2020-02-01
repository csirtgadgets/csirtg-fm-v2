from csirtg_fm import FM
from csirtg_fm.content import get_type
from csirtg_fm.utils import decode
from csirtg_dt import get as parse_timestamp

rule = 'test/fm/phishtank/phishtank.yml'
s = FM()


def test_phishtank_urls():
    indicators = set()
    tags = set()

    from csirtg_fm.clients.http import Client
    cli = Client(rule, 'urls')
    cli.cache = decode(cli.cache)
    cli.cache = 'test/fm/phishtank/feed.json'

    parser_name = get_type(cli.cache)
    assert parser_name == 'json'

    for i in s.process(rule, 'urls', parser_name, cli):
        if not i:
            continue

        assert parse_timestamp(i.reported_at).year > 1980
        assert parse_timestamp(i.last_at).year > 1980
        assert parse_timestamp(i.first_at).year > 1980

        indicators.add(i.indicator)
        tags.add(i.tags[0])

    assert 'http://charlesleonardconstruction.com/irs/confim/index.html' in \
           indicators
