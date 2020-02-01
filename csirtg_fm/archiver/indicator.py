from arrow import get as get_ts

from sqlalchemy import Column, Integer, DateTime, UnicodeText, Text
from sqlalchemy.sql.expression import func

from csirtg_fm.archiver.constants import BASE


class Indicator(BASE):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True)
    indicator = Column(UnicodeText, index=True)
    group = Column(Text)
    provider = Column(Text)
    first_at = Column(DateTime)
    last_at = Column(DateTime)
    tags = Column(Text)
    created_at = Column(DateTime, default=func.now())

    def __init__(self, indicator=None, group='everyone', provider=None,
                 first_at=None, last_at=None, tags=None):

        self.indicator = indicator
        self.group = group
        self.provider = provider
        self.first_at = first_at
        self.last_at = last_at
        self.tags = tags

        if isinstance(group, list):
            self.group = group[0]

        if isinstance(self.tags, list):
            self.tags.sort()
            self.tags = ','.join(self.tags)

        if self.last_at and isinstance(self.last_at, (str, bytes)):
            self.last_at = get_ts(self.last_at).datetime

        if self.first_at and isinstance(self.first_at, (str, bytes)):
            self.first_at = get_ts(self.first_at).datetime
