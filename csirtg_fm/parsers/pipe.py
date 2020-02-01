from csirtg_fm.parsers.delim import Delim


class Pipe(Delim):
    delim = r"\s{2,}|\s{2,}"

    def __init__(self, **kwargs):
        super(Pipe, self).__init__(**kwargs)


Plugin = Pipe
