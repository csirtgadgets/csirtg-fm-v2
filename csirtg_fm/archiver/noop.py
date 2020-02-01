
class NOOPArchiver:
    def __init__(self, *args, **kwargs):
        pass

    def begin(self):
        pass

    def commit(self):
        pass

    def clear_memcache(self):
        pass

    def search(self, indicator):
        return False

    def create(self, indicator):
        pass

    def cleanup(self, days=180):
        return 0
