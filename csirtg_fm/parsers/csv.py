from csirtg_fm.parsers.delim import Delim


class Csv(Delim):
    delim = ","
    strip = '"'

    def __init__(self, **kwargs):
        super(Csv, self).__init__(**kwargs)


Plugin = Csv
