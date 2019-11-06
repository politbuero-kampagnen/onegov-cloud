from datetime import datetime
from sedate import utcnow
from sqlalchemy import desc

from onegov.core.collection import Pagination, GenericCollection
from onegov.fsi.models.course_event import CourseEvent
from onegov.fsi.models.reservation import Reservation


class CourseEventCollection(GenericCollection, Pagination):

    def __init__(
            self, session,
            page=0,
            creator=None,
            from_date=None,
            upcoming_only=True,
            past_only=False,
            limit=None
    ):
        super().__init__(session)
        self.page = page
        # filter newer than from date
        self.from_date = from_date              # ignores upcoming_only
        self.upcoming_only = upcoming_only      # active if from_date not set
        self.past_only = past_only
        self.limit = limit

        if from_date:
            assert isinstance(from_date, datetime)

    # def __eq__(self, other):
    #     return (self.page == other.page
    #             and self.creator == other.creator
    #             and self.from_date == other.from_date
    #             and self.upcoming_only == other.upcoming_only
    #             and self.past_only == other.past_only
    #             and self.limit
    #             )

    @property
    def model_class(self):
        return CourseEvent

    def query(self):
        query = super().query()
        if self.from_date:
            query = query.filter(CourseEvent.start > self.from_date)
        elif self.past_only:
            query = query.filter(CourseEvent.start <= utcnow())
        elif self.upcoming_only:
            query = query.filter(CourseEvent.start >= utcnow())

        query = query.order_by(desc(CourseEvent.start))

        if self.limit:
            query = query.limit(self.limit)

        return query

    def subset(self):
        return self.query()

    @property
    def page_index(self):
        return self.page

    def page_by_index(self, index):
        return self.__class__(
            self.session, index,
            from_date=self.from_date,
            upcoming_only=self.upcoming_only,
            past_only=self.past_only,
            limit=self.limit
        )

    def add_placeholder(self, title, course_event):
        assert isinstance(course_event, CourseEvent)
        reservation = Reservation.as_placeholder(
            dummy_desc=title, course_event_id=course_event.id)
        self.session.add(reservation)
        self.session.flush()

    @classmethod
    def latest(cls, session):
        return cls(session, upcoming_only=True, limit=5)
