import json

from itertools import groupby
from onegov.activity import Activity, AttendeeCollection
from onegov.activity import Booking
from onegov.activity import BookingCollection
from onegov.activity import Occasion
from onegov.activity import OccasionCollection
from onegov.core.security import Personal
from onegov.core.templates import render_macro
from onegov.core.utils import normalize_for_url
from onegov.feriennet import FeriennetApp, _
from onegov.feriennet.layout import BookingCollectionLayout
from onegov.org.elements import DeleteLink
from sqlalchemy import desc
from sqlalchemy.orm import contains_eager


def all_bookings(collection):
    """ Loads all bookings together with the linked occasions, attendees and
    activities. This is somewhat of a heavy query, but it beats having to
    load all these things separately.

    """
    query = collection.query()

    query = query.join(Booking.attendee)
    query = query.join(Booking.occasion)
    query = query.join(Occasion.activity)

    query = query.options(contains_eager(Booking.attendee))
    query = query.options(
        contains_eager(Booking.occasion).
        contains_eager(Occasion.activity))

    query = query.order_by(Booking.attendee_id)
    query = query.order_by(Activity.name)
    query = query.order_by(Occasion.start)

    return query.all()


def group_bookings_by_attendee(bookings):
    """ Takes a list of bookings and groups them by attendee. """

    return {
        attendee: tuple(bookings)
        for attendee, bookings
        in groupby(bookings, key=lambda b: b.attendee)
    }


def attendees_by_username(request, username):
    """ Loads the given attendees linked to the given username, sorted by
    their name.

    """

    a = AttendeeCollection(request.app.session()).by_username(username).all()
    a.sort(key=lambda a: normalize_for_url(a.name))

    return a


def actions_by_booking(layout, booking):
    actions = []

    if booking.state == 'unconfirmed':
        actions.append(DeleteLink(
            text=_("Remove"),
            url=layout.csrf_protected_url(layout.request.link(booking)),
            confirm=_('Do you really want to remove "${title}"?', mapping={
                'title': "{} - {}".format(
                    booking.occasion.activity.title,
                    layout.format_datetime_range(
                        booking.occasion.start,
                        booking.occasion.end))
            }),
            yes_button_text=_("Remove Booking"),
            classes=('confirm', ),
            target='#booking-{}'.format(booking.id)
        ))

    return actions


def show_error_on_attendee(request, attendee, message):
    @request.after
    def show_error(response):
        response.headers.add('X-IC-Trigger', 'show-alert')
        response.headers.add('X-IC-Trigger-Data', json.dumps({
            'type': 'alert',
            'target': '#alert-boxes-for-{}'.format(attendee.id),
            'message': request.translate(message)
        }))


@FeriennetApp.html(
    model=BookingCollection,
    template='bookings.pt',
    permission=Personal)
def view_my_bookings(self, request):
    attendees = attendees_by_username(request, self.username)

    bookings = all_bookings(self)
    bookings_by_attendee = group_bookings_by_attendee(bookings)

    period = bookings and bookings[0].occasion.period or None
    layout = BookingCollectionLayout(self, request)

    return {
        'actions_by_booking': lambda b: actions_by_booking(layout, b),
        'attendees': attendees,
        'bookings_by_attendee': bookings_by_attendee.get,
        'has_bookings': bookings and True or False,
        'layout': layout,
        'period': period,
        'title': _("My Bookings"),
    }


@FeriennetApp.view(
    model=Booking,
    permission=Personal,
    request_method='DELETE')
def delete_booking(self, request):
    request.assert_valid_csrf_token()

    if self.state != 'unconfirmed':
        show_error_on_attendee(request, self.attendee, _(
            "Only unconfirmed bookings may be deleted"))

        return

    BookingCollection(request.app.session()).delete(self)

    @request.after
    def remove_target(response):
        response.headers.add('X-IC-Remove', 'true')


@FeriennetApp.view(
    model=Booking,
    name='toggle-star',
    permission=Personal,
    request_method='POST')
def toggle_star(self, request):

    # only up to three bookings per attendee may be favorited
    if self.priority == 0:
        o = OccasionCollection(request.app.session()).query()
        o = o.with_entities(Occasion.id)
        o = o.filter(Occasion.period_id == self.occasion.period_id)
        o = o.subquery()

        q = BookingCollection(request.app.session()).query()
        q = q.filter(Booking.attendee_id == self.attendee_id)
        q = q.filter(Booking.username == self.username)
        q = q.filter(Booking.occasion_id.in_(o))
        q = q.filter(Booking.id != self.id)
        q = q.filter(Booking.priority != 0)
        q = q.order_by(desc(Booking.last_change))

        if q.count() < 3:
            self.priority = 1
        else:
            show_error_on_attendee(request, self.attendee, _(
                "Cannot select more than three favorites per child"))
    else:
        self.priority = 0

    layout = BookingCollectionLayout(self, request)
    return render_macro(layout.macros['star'], request, {'booking': self})
