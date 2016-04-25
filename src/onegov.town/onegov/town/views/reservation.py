import json
import morepath
import sedate

from datetime import time
from libres.db.models import Allocation, Reservation
from libres.modules.errors import LibresError
from onegov.core.security import Public, Private
from onegov.form import FormCollection, merge_forms
from onegov.libres import Resource, ResourceCollection
from onegov.ticket import TicketCollection
from onegov.town import TownApp, _, utils
from onegov.town.elements import Link
from onegov.town.forms import ReservationForm
from onegov.town.layout import ReservationLayout
from onegov.town.mail import send_html_mail
from sqlalchemy.orm.attributes import flag_modified
from webob import exc


def get_reservation_form_class(resource, request):
    if resource.definition:
        return merge_forms(ReservationForm, resource.form_class)
    else:
        return ReservationForm


def assert_anonymous_access_only_temporary(self, request):
    """ Raises exceptions if the current user is anonymous and no longer
    should be given access to the reservation models.

    This could probably be done using morepath's security system, but it would
    not be quite as straight-forward. This approach is, though we have
    to manually add this function to all reservation views the anonymous user
    should be able to access when creating a new reservatin, but not anymore
    after that.

    """
    if request.is_logged_in:
        return

    if not self.session_id:
        raise exc.HTTPForbidden()

    if self.status == 'approved':
        raise exc.HTTPForbidden()

    if self.session_id != utils.get_libres_session_id(request):
        raise exc.HTTPForbidden()


@TownApp.json(model=Allocation, name='reserve', request_method='POST',
              permission=Public)
def reserve_allocation(self, request):

    collection = ResourceCollection(request.app.libres_context)
    resource = collection.by_id(self.resource)

    scheduler = resource.get_scheduler(request.app.libres_context)

    start = request.params.get('start') or '{:%H:%M}'.format(self.start)
    end = request.params.get('end') or '{:%H:%M}'.format(self.end)
    quota = int(request.params.get('quota', 1))
    whole_day = request.params.get('whole_day') == '1'

    if self.partly_available:
        if self.whole_day and whole_day:
            start = time(0, 0)
            end = time(23, 59)
        else:
            start = sedate.parse_time(start)
            end = sedate.parse_time(end)

        start, end = sedate.get_date_range(
            sedate.to_timezone(self.start, self.timezone), start, end
        )
    else:
        start = self.start, self.end

    try:
        scheduler.reserve(
            email='0xdeadbeef@example.org',  # will be set later
            dates=(start, end),
            quota=quota,
            session_id=utils.get_libres_session_id(request)
        )
    except LibresError as e:
        message = {
            'message': utils.get_libres_error(e, request),
            'success': False
        }

        @request.after
        def trigger_calendar_update(response):
            response.headers.add('X-IC-Trigger', 'rc-reservation-error')
            response.headers.add('X-IC-Trigger-Data', json.dumps(message))

        return message
    else:

        @request.after
        def trigger_calendar_update(response):
            response.headers.add('X-IC-Trigger', 'rc-reservations-changed')

        return {
            'success': True
        }


@TownApp.json(model=Reservation, request_method='DELETE', permission=Public)
def delete_reservation(self, request):

    # this view is public, but only for a limited time
    assert_anonymous_access_only_temporary(self, request)

    collection = ResourceCollection(request.app.libres_context)
    resource = collection.by_id(self.resource)

    scheduler = resource.get_scheduler(request.app.libres_context)

    try:
        scheduler.remove_reservation(self.token, self.id)
    except LibresError as e:
        message = {
            'message': utils.get_libres_error(e, request),
            'success': False
        }

        @request.after
        def trigger_calendar_update(response):
            response.headers.add('X-IC-Trigger', 'rc-reservation-error')
            response.headers.add('X-IC-Trigger-Data', json.dumps(message))

        return message
    else:

        @request.after
        def trigger_calendar_update(response):
            response.headers.add('X-IC-Trigger', 'rc-reservations-changed')

        return {
            'success': True
        }


@TownApp.form(model=Resource, name='formular', template='reservation_form.pt',
              permission=Public, form=get_reservation_form_class)
def handle_reservation_form(self, request, form):
    """ Asks the user for the form data required to complete one or many
    reservations on a resource.

    """
    reservations = self.get_reservations(request)

    if form.submitted(request):

        # update the e-mail data
        for reservation in reservations:
            reservation.email = form.email.data

        # while we re at it, remove all expired sessions
        self.remove_expired_reservation_sessions(request.app.libres_context)

        if self.definition:
            forms = FormCollection(request.app.session())
            submission = forms.submissions.add_external(
                form=self.form_class(),
                state='pending',
                id=reservation.token
            )
            forms.submissions.update(
                submission, form, exclude=form.reserved_fields
            )

        return morepath.redirect(request.link(reservation, 'bestaetigung'))

    layout = ReservationLayout(self, request)
    layout.breadcrumbs.append(Link(_("Reserve"), '#'))

    title = _("New dates for ${title}", mapping={
        'title': self.title,
    })

    return {
        'layout': layout,
        'title': title,
        'form': form,
        'reservations': [
            utils.ReservationInfo(r, request) for r in reservations
        ],
        'resource': self,
        'button_text': _("Continue")
    }


@TownApp.html(model=Reservation, name='bestaetigung', permission=Public,
              template='reservation_confirmation.pt')
def confirm_reservation(self, request):

    # this view is public, but only for a limited time
    assert_anonymous_access_only_temporary(self, request)

    collection = ResourceCollection(request.app.libres_context)
    resource = collection.by_id(self.resource)

    forms = FormCollection(request.app.session())
    submission = forms.submissions.by_id(self.token)

    if submission:
        form = request.get_form(submission.form_class, data=submission.data)
    else:
        form = None

    layout = ReservationLayout(resource, request)
    layout.breadcrumbs.append(Link(_("Confirm"), '#'))

    return {
        'title': _("Confirm your reservation"),
        'layout': layout,
        'form': form,
        'resource': resource,
        'allocation': self._target_allocations().first(),
        'reservation': self,
        'finalize_link': request.link(self, 'abschluss'),
        'edit_link': request.link(self, 'bearbeiten'),
        'is_whole_day_reservation': sedate.is_whole_day(
            self.display_start(),
            self.display_end(),
            self.timezone
        )
    }


@TownApp.html(model=Reservation, name='abschluss', permission=Public,
              template='layout.pt')
def finalize_reservation(self, request):

    # this view is public, but only for a limited time
    assert_anonymous_access_only_temporary(self, request)

    collection = ResourceCollection(request.app.libres_context)
    resource = collection.by_id(self.resource)
    scheduler = resource.get_scheduler(request.app.libres_context)
    session_id = utils.get_libres_session_id(request)

    try:
        scheduler.queries.confirm_reservations_for_session(session_id)
        scheduler.approve_reservations(self.token)
    except LibresError as e:
        utils.show_libres_error(e, request)

        layout = ReservationLayout(resource, request)
        layout.breadcrumbs.append(Link(_("Error"), '#'))

        return {
            'title': _("The reservation could not be completed"),
            'layout': layout,
        }
    else:
        forms = FormCollection(request.app.session())
        submission = forms.submissions.by_id(self.token)

        if submission:
            forms.submissions.complete_submission(submission)

        with forms.session.no_autoflush:
            ticket = TicketCollection(request.app.session()).open_ticket(
                handler_code='RSV', handler_id=self.token.hex
            )

        send_html_mail(
            request=request,
            template='mail_ticket_opened.pt',
            subject=_("A ticket has been opened"),
            receivers=(self.email, ),
            content={
                'model': ticket
            }
        )

        request.success(_("Thank you for your reservation!"))
        request.app.update_ticket_count()

        return morepath.redirect(request.link(ticket, 'status'))


@TownApp.view(model=Reservation, name='annehmen', permission=Private)
def accept_reservation(self, request):
    if not self.data or not self.data.get('accepted'):
        collection = ResourceCollection(request.app.libres_context)
        resource = collection.by_id(self.resource)
        scheduler = resource.get_scheduler(request.app.libres_context)
        reservations = scheduler.reservations_by_token(self.token)

        send_html_mail(
            request=request,
            template='mail_reservation_accepted.pt',
            subject=_("Your reservation was accepted"),
            receivers=(self.email, ),
            content={
                'model': self,
                'resource': resource,
                'reservations': reservations
            }
        )

        for reservation in reservations:
            reservation.data = reservation.data or {}
            reservation.data['accepted'] = True

            # libres does not automatically detect changes yet
            flag_modified(reservation, 'data')

        request.success(_("The reservation was accepted"))
    else:
        request.warning(_("The reservation has already been accepted"))

    return morepath.redirect(request.params['return-to'])


@TownApp.view(model=Reservation, name='absagen', permission=Private)
def reject_reservation(self, request):
    collection = ResourceCollection(request.app.libres_context)
    resource = collection.by_id(self.resource)
    scheduler = resource.get_scheduler(request.app.libres_context)
    reservations = scheduler.reservations_by_token(self.token.hex)
    forms = FormCollection(request.app.session())
    submission = forms.submissions.by_id(self.token.hex)

    send_html_mail(
        request=request,
        template='mail_reservation_rejected.pt',
        subject=_("Your reservation was rejected"),
        receivers=(self.email, ),
        content={
            'model': self,
            'resource': resource,
            'reservations': reservations
        }
    )

    # create a snapshot of the ticket to keep the useful information
    tickets = TicketCollection(request.app.session())
    ticket = tickets.by_handler_id(self.token.hex)
    ticket.create_snapshot(request)

    scheduler.remove_reservation(self.token.hex)

    if submission:
        forms.submissions.delete(submission)

    request.success(_("The reservation was rejected"))

    # return none on intercooler js requests
    if not request.headers.get('X-IC-Request'):
        return morepath.redirect(request.params['return-to'])
