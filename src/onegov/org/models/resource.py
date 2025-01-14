import sedate

from datetime import datetime

from libres.db.models import ReservedSlot

from onegov.core.orm.mixins import meta_property, content_property
from onegov.core.orm.types import UUID
from onegov.form.models import FormSubmission
from onegov.org.models.extensions import ContactExtension, \
    ResourceValidationExtension
from onegov.org.models.extensions import CoordinatesExtension
from onegov.org.models.extensions import AccessExtension
from onegov.org.models.extensions import PersonLinkExtension
from onegov.reservation import Resource, Reservation
from onegov.search import SearchableContent
from onegov.ticket import Ticket
from sqlalchemy.orm import undefer
from sqlalchemy.sql.expression import cast
from uuid import uuid4, uuid5


class SharedMethods(object):

    lead = meta_property()
    text = content_property()

    @property
    def deletable(self):
        if self.scheduler.managed_reserved_slots().first():
            return False

        if self.scheduler.managed_reservations().first():
            return False

        return True

    @property
    def future_managed_reservations(self):
        return self.scheduler.managed_reservations().filter(
            Reservation.end >= sedate.utcnow())

    @property
    def future_managed_reserved_slots(self):
        return self.scheduler.managed_reserved_slots().filter(
            ReservedSlot.end >= sedate.utcnow())

    @property
    def calendar_date_range(self):
        """ Returns the date range set by the fullcalendar specific params. """

        if self.date:
            date = datetime(self.date.year, self.date.month, self.date.day)
            date = sedate.replace_timezone(date, self.timezone)
        else:
            date = sedate.to_timezone(sedate.utcnow(), self.timezone)

        if self.view == 'month':
            return sedate.align_range_to_month(date, date, self.timezone)
        elif self.view == 'agendaWeek':
            return sedate.align_range_to_week(date, date, self.timezone)
        elif self.view == 'agendaDay':
            return sedate.align_range_to_day(date, date, self.timezone)
        else:
            raise NotImplementedError()

    def remove_expired_reservation_sessions(self, expiration_date=None):
        session = self.libres_context.get_service('session_provider').session()
        queries = self.scheduler.queries

        expired_sessions = queries.find_expired_reservation_sessions(
            expiration_date)

        if expired_sessions:
            query = session.query(Reservation).with_entities(Reservation.token)
            query = query.filter(Reservation.session_id.in_(expired_sessions))
            tokens = set(r[0] for r in query.all())

            query = session.query(FormSubmission)
            query = query.filter(FormSubmission.name == None)
            query = query.filter(FormSubmission.id.in_(tokens))

            query.delete('fetch')
            queries.remove_expired_reservation_sessions(expiration_date)

    def bound_reservations(self, request, status='pending'):
        """ The reservations associated with this resource and user. """

        session = self.bound_session_id(request)
        scheduler = self.get_scheduler(request.app.libres_context)

        res = scheduler.queries.reservations_by_session(session)
        res = res.filter(Reservation.resource == self.id)
        res = res.filter(Reservation.status == status)
        res = res.order_by(None)  # clear existing order
        res = res.order_by(Reservation.start)

        # used by ReservationInfo
        res = res.options(undefer(Reservation.created))

        return res

    def bound_session_id(self, request):
        """ The session id associated with this resource and user. """
        if not request.browser_session.has('libres_session_id'):
            request.browser_session.libres_session_id = uuid4()

        return uuid5(self.id, request.browser_session.libres_session_id.hex)

    def reservations_with_tickets_query(self, start=None, end=None):
        """ Returns a query which joins this resource's reservations between
        start and end with the tickets table.

        """
        query = self.scheduler.managed_reservations()
        if start:
            query = query.filter(start <= Reservation.start)
        if end:
            query = query.filter(Reservation.end <= end)

        query = query.join(
            Ticket, Reservation.token == cast(Ticket.handler_id, UUID))

        query = query.order_by(Reservation.start)
        query = query.order_by(Ticket.subtitle)
        query = query.filter(Reservation.status == 'approved')
        query = query.filter(Reservation.data != None)

        return query

    def reservation_title(self, reservation):
        title = self.title_template.format(
            start=reservation.display_start(),
            end=reservation.display_end(),
            quota=reservation.quota
        )

        if title.endswith('00:00'):
            return title[:-5] + '24:00'

        return title


class DaypassResource(Resource, AccessExtension, SearchableContent,
                      ContactExtension, PersonLinkExtension,
                      CoordinatesExtension, SharedMethods,
                      ResourceValidationExtension):
    __mapper_args__ = {'polymorphic_identity': 'daypass'}

    es_type_name = 'daypasses'

    # the selected view
    view = 'month'

    # show or hide quota numbers in reports
    show_quota = True

    # use to render the reservation title
    title_template = '{start:%d.%m.%Y} ({quota})'


class RoomResource(Resource, AccessExtension, SearchableContent,
                   ContactExtension, PersonLinkExtension,
                   CoordinatesExtension, SharedMethods,
                   ResourceValidationExtension):
    __mapper_args__ = {'polymorphic_identity': 'room'}

    es_type_name = 'rooms'

    # the selected view (depends on the resource's default)
    view = None

    # show or hide quota numbers in reports
    show_quota = False

    # used to render the reservation title
    title_template = '{start:%d.%m.%Y} {start:%H:%M} - {end:%H:%M}'

    @property
    def deletable(self):
        if self.future_managed_reserved_slots.first():
            return False

        if self.future_managed_reservations.first():
            return False

        return True


class ItemResource(Resource, AccessExtension, SearchableContent,
                   ContactExtension, PersonLinkExtension,
                   CoordinatesExtension, SharedMethods,
                   ResourceValidationExtension):

    __mapper_args__ = {'polymorphic_identity': 'daily-item'}

    es_type_name = 'daily_items'

    view = None

    show_quota = True

    title_template = '{start:%d.%m.%Y} {start:%H:%M} - {end:%H:%M} ({quota})'
