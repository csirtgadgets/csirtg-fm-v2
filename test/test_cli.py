from csirtg_fm.cli import FM
from csirtg_fm.clients import apwg, csirtg


def test_cli():
    FM()
    apwg.Client()
    csirtg.Client()
    # cif.HTTPClient()
    # cifzmq.CIF()
