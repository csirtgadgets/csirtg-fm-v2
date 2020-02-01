from cifsdk.client.zeromq import ZMQ


class CIF(ZMQ):

    def __init__(self, **kwargs):
        kwargs['nowait'] = True
        kwargs['autoclose'] = False
        kwargs['fireball'] = True

        super(CIF, self).__init__(**kwargs)

    def ping(self):
        return self.ping()

    def ping_write(self):
        return self.ping_write()


Plugin = CIF
