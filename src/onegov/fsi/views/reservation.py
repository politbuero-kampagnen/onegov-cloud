from onegov.fsi import FsiApp
from onegov.fsi.collections.reservation import ReservationCollection
from onegov.fsi.layouts.reservation import ReservationLayout, \
    ReservationCollectionLayout
from onegov.fsi.models.reservation import Reservation
from onegov.org.forms import ReservationForm
from onegov.fsi import _


@FsiApp.html(model=ReservationCollection, template='reservations.pt')
def view_reservations(self, request):
    layout = ReservationCollectionLayout(self, request)
    return {
        'title': _('Reservations'),
        'layout': layout,
        'reservations': self.query().all()
    }


@FsiApp.html(
    model=ReservationCollection,
    template='form.pt',
    name='add',
    form=ReservationForm
)
def view_add_reservation(self, request):
    layout = ReservationLayout(self, request)
    return {
        'title': _('Add Reservation'),
        'layout': layout,
        'model': self,
    }


@FsiApp.html(
    model=ReservationCollection,
    request_method='POST',
    name='add-from-course-event'
)
def view_add_from_course_event(self, request):
    request.assert_valid_csrf_token()
    self.add(
        attendee_id=self.attendee_id or request.attendee_id,
        course_event_id=self.course_event_id)
    request.success(_('New reservation successfully added'))


@FsiApp.html(model=Reservation)
def view_reservation(self, request):
    pass


@FsiApp.html(
    model=Reservation,
    request_method='DELETE',
    name='delete'
)
def view_delete_reservation(self, request):
    request.assert_valid_csrf_token()
    ReservationCollection(request.session).delete(self)
    request.success(_('Reservation successfully deleted'))
