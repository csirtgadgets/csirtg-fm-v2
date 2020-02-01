from csirtgsdk.client.http import HTTP as CSIRTGClient
from csirtgsdk.feed import Feed
from csirtg_fm.constants import VERSION
from pprint import pprint


class Client(object):
    def __init__(self, **kwargs):
        self.handle = CSIRTGClient()
        self.handle.session.headers['User-Agent'] = 'csirtg-fm/%s' % VERSION

    def fetch(self, user, feed, limit=50):
        data = Feed(self.handle).show(user, feed, limit=limit)
        data = data['indicators']
        for i in data:
            i['provider'] = 'csirtg.io'
            i['reference'] = 'https://csirtg.io/users/%s/feeds/%s' % (user,
                                                                      feed)
            i['tlp'] = i.get('tlp', 'green')

        return data
