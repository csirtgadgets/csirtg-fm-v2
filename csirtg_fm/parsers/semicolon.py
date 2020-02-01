from csirtg_fm.parsers.delim import Delim


class Semicolon(Delim):
    delim = r"[\s+]?;[\s+]?"

    def __init__(self, **kwargs):
        super(Semicolon, self).__init__(**kwargs)


Plugin = Semicolon
