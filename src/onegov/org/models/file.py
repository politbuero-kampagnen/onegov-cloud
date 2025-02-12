""" Contains the models describing files and images. """

import sedate

from cached_property import cached_property
from collections import namedtuple
from datetime import datetime
from dateutil.relativedelta import relativedelta
from itertools import chain, groupby
from onegov.core.orm import as_selectable
from onegov.core.orm.mixins import meta_property
from onegov.file import File, FileSet, FileCollection, FileSetCollection
from onegov.file import SearchableFile
from onegov.file.utils import IMAGE_MIME_TYPES_AND_SVG
from onegov.org import _
from onegov.org.models.extensions import AccessExtension
from onegov.search import ORMSearchable
from sedate import standardize_date, utcnow
from sqlalchemy import asc, desc, select


DateInterval = namedtuple('DateInterval', ('name', 'start', 'end'))


class GroupFilesByDateMixin(object):

    def get_date_intervals(self, today):
        today = standardize_date(today, 'UTC')

        month_end = today + relativedelta(day=31)
        month_start = today - relativedelta(day=1)

        yield DateInterval(
            name=_("This month"),
            start=month_start,
            end=month_end)

        last_month_end = month_start - relativedelta(microseconds=1)
        last_month_start = month_start - relativedelta(months=1)

        yield DateInterval(
            name=_("Last month"),
            start=last_month_start,
            end=last_month_end)

        if month_start.month not in (1, 2):
            this_year_end = last_month_start - relativedelta(microseconds=1)
            this_year_start = this_year_end.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

            yield DateInterval(
                name=_("This year"),
                start=this_year_start,
                end=this_year_end)
        else:
            this_year_end = None
            this_year_start = None

        last_year_end = this_year_start or last_month_start
        last_year_end -= relativedelta(microseconds=1)
        last_year_start = last_year_end.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        yield DateInterval(
            name=_("Last year"),
            start=last_year_start,
            end=last_year_end)

        older_end = last_year_start - relativedelta(microseconds=1)
        older_start = datetime(2000, 1, 1, tzinfo=today.tzinfo)

        yield DateInterval(
            name=_("Older"),
            start=older_start,
            end=older_end)

    def query_intervals(self, intervals, before_filter=None, process=None):
        base_query = self.query().order_by(desc(File.created))

        if before_filter:
            base_query = before_filter(base_query)

        for interval in intervals:
            query = base_query.filter(File.created >= interval.start)
            query = query.filter(File.created <= interval.end)

            for result in query.all():
                if process is not None:
                    yield interval.name, process(result)

    def grouped_by_date(self, today=None, id_only=True):
        """ Returns all files grouped by natural language dates.

        By default, only ids are returned, as this is enough to build the
        necessary links, which is what you usually want from a file.

        The given date is expected to be in UTC.

        """

        intervals = tuple(self.get_date_intervals(today or utcnow()))

        def before_filter(query):
            if id_only:
                return query.with_entities(File.id)

            return query

        def process(result):
            if id_only:
                return result.id

            return result

        return groupby(
            self.query_intervals(intervals, before_filter, process),
            key=lambda item: item[0]
        )


class GeneralFile(File, SearchableFile):
    __mapper_args__ = {'polymorphic_identity': 'general'}

    @property
    def es_public(self):
        return self.published and self.publication


class ImageFile(File):
    __mapper_args__ = {'polymorphic_identity': 'image'}


class ImageSet(FileSet, AccessExtension, ORMSearchable):
    __mapper_args__ = {'polymorphic_identity': 'image'}

    es_properties = {
        'title': {'type': 'localized'},
        'lead': {'type': 'localized'}
    }

    @property
    def es_public(self):
        return self.access == 'public'

    @property
    def es_suggestions(self):
        return {
            "input": [self.title.lower()]
        }

    lead = meta_property()
    view = meta_property()

    show_images_on_homepage = meta_property()


class ImageSetCollection(FileSetCollection):

    def __init__(self, session):
        super().__init__(session, type='image')


class GeneralFileCollection(FileCollection, GroupFilesByDateMixin):

    supported_content_types = 'all'

    file_list = as_selectable("""
        SELECT
            row_number() OVER () as number, -- Integer
            id,                             -- Text
            name,                           -- Text
            "order",                        -- Text
            signed,                         -- Boolean
            created as upload_date,         -- UTCDateTime
            reference->>'content_type'
                AS content_type             -- Text
        FROM files
        WHERE type = 'general'
    """)

    def __init__(self, session, order_by='name'):
        super().__init__(session, type='general', allow_duplicates=False)

        self.order_by = order_by
        self.direction = order_by == 'name' and 'ascending' or 'descending'

        self._last_interval = None

    def for_order(self, order):
        return self.__class__(self.session, order_by=order)

    @cached_property
    def intervals(self):
        return tuple(self.get_date_intervals(today=sedate.utcnow()))

    @property
    def statement(self):
        stmt = select(self.file_list.c)

        if self.order_by == 'name':
            order = self.file_list.c.order
        else:
            order = self.file_list.c.upload_date

        direction = self.direction == 'ascending' and asc or desc

        return stmt.order_by(direction(order))

    @property
    def files(self):
        return self.session.execute(self.statement)

    def group(self, record):
        if self.order_by == 'name':
            if record.order[0].isdigit():
                return '0-9'

            return record.order[0].upper()
        else:
            if self._last_interval:
                intervals = chain((self._last_interval, ), self.intervals)
            else:
                intervals = self.intervals

            for interval in intervals:
                if interval.start <= record.upload_date <= interval.end:
                    break
            else:
                return _("Older")

            # this method is usually called for each item in a sorted set,
            # we optimise for that by caching the last matching interval
            # and checking that one first the next time
            self._last_interval = interval

            return interval.name


class ImageFileCollection(FileCollection, GroupFilesByDateMixin):

    supported_content_types = IMAGE_MIME_TYPES_AND_SVG

    def __init__(self, session):
        super().__init__(session, type='image', allow_duplicates=False)
