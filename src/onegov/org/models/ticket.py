from cached_property import cached_property
from onegov.core.templates import render_macro
from onegov.directory import Directory, DirectoryEntry
from onegov.event import EventCollection
from onegov.form import FormSubmissionCollection
from onegov.org import _
from onegov.org.layout import DefaultLayout, EventLayout
from onegov.chat import Message
from onegov.core.elements import Link, LinkGroup, Confirm, Intercooler
from onegov.reservation import Allocation, Resource, Reservation
from onegov.ticket import Ticket, Handler, handlers
from onegov.search.utils import extract_hashtags
from purl import URL
from sqlalchemy.orm import object_session


class TicketDeletionMixin:

    @property
    def ticket_deletable(self):
        return self.deleted and self.ticket.state == 'archived'

    def prepare_delete_ticket(self):
        """The handler knows best what to do when a ticket is called for
        deletion. """
        assert self.ticket_deletable
        pass


def ticket_submitter(ticket):
    handler = ticket.handler
    mail = handler.deleted and ticket.snapshot.get('email') or handler.email
    # case of EventSubmissionHandler for imported events
    if handler.data.get('source'):
        mail = handler.data.get('user', mail)
    return mail


class OrgTicketMixin(object):
    """ Adds additional methods to the ticket, needed by the organisations
    implementation of it. Strictly limited to things that
    do not belong into onegov.ticket.

    """

    def reference(self, request):
        """ Returns the reference which should be used wherever we talk about
        a ticket, but do not show it (say in an e-mail subject).

        This reference should not be changed so it stays consistent.

        If you want, you can override the content of the reference group,
        shown in brackets (see :meth:`reference_group`).

        """
        return f'{self.number} / {self.reference_group(request)}'

    def reference_group(self, request):
        return request.translate(self.group)

    @cached_property
    def extra_localized_text(self):

        # extracts of attachments are currently not searchable - if they were
        # we would add this here - probably in a raw SQL query that
        # concatenates all the text
        #
        # for now I've decided against it as it would lower the hit-rate
        # for notes (which should be very easy to find), just to be able
        # to search through files which are mostly going to be irrelevant
        # for what the user wants to find
        #
        # if the user wants to have a ticket findable through the file content
        # we should advise them to enter a meaningful note with the file
        # instead.
        #
        q = object_session(self).query(Message)
        q = q.filter_by(channel_id=self.number)
        q = q.filter(Message.type.in_(('ticket_note', 'ticket_chat')))
        q = q.with_entities(Message.text)

        return ' '.join(n.text for n in q if n.text)

    @property
    def es_tags(self):
        if self.extra_localized_text:
            return [
                tag.lstrip('#') for tag in extract_hashtags(
                    self.extra_localized_text
                )
            ]


class FormSubmissionTicket(OrgTicketMixin, Ticket):
    __mapper_args__ = {'polymorphic_identity': 'FRM'}
    es_type_name = 'submission_tickets'


class ReservationTicket(OrgTicketMixin, Ticket):
    __mapper_args__ = {'polymorphic_identity': 'RSV'}
    es_type_name = 'reservation_tickets'


class EventSubmissionTicket(OrgTicketMixin, Ticket):
    __mapper_args__ = {'polymorphic_identity': 'EVN'}
    es_type_name = 'event_tickets'

    def reference_group(self, request):
        return self.title


class DirectoryEntryTicket(OrgTicketMixin, Ticket):
    __mapper_args__ = {'polymorphic_identity': 'DIR'}
    es_type_name = 'directory_tickets'


@handlers.registered_handler('FRM')
class FormSubmissionHandler(Handler, TicketDeletionMixin):

    handler_title = _("Form Submissions")
    code_title = _("Forms")

    @cached_property
    def collection(self):
        return FormSubmissionCollection(self.session)

    @cached_property
    def submission(self):
        return self.collection.by_id(self.id)

    @cached_property
    def form(self):
        return self.submission.form_class(data=self.submission.data)

    @property
    def deleted(self):
        return self.submission is None

    @property
    def email(self):
        return self.submission.email

    @property
    def title(self):
        return self.submission.title

    @property
    def subtitle(self):
        return None

    @property
    def group(self):
        return self.submission.form.title

    @property
    def payment(self):
        return self.submission and self.submission.payment

    @property
    def extra_data(self):
        return self.submission and [
            v for v in self.submission.data.values()
            if isinstance(v, str)
        ]

    @property
    def undecided(self):
        if self.deleted:
            return False

        # submissions without registration window do not present a decision
        if not self.submission.registration_window:
            return False

        if self.submission.claimed is None:
            return True

        return False

    def prepare_delete_ticket(self):
        if self.submission:
            for file in self.submission.files:
                self.session.delete(file)
            self.session.delete(self.submission)

    @property
    def ticket_deletable(self):
        """Todo: Finalize implementing ticket deletion """
        if self.deleted:
            return True
        return False
        #  ...for later when deletion will be available
        if not self.ticket.state == 'archived':
            return False
        if self.payment:
            # For now we do not handle this case since payment might be
            # needed for exports
            return False
        if self.undecided:
            return False
        return True

    def get_summary(self, request):
        layout = DefaultLayout(self.submission, request)

        return render_macro(layout.macros['display_form'], request, {
            'form': self.form,
            'layout': layout
        })

    def get_links(self, request):
        layout = DefaultLayout(self.submission, request)

        links = []
        extra = []

        # there's a decision to be made about the registration
        window = self.submission.registration_window

        if window:
            if self.submission.spots and self.submission.claimed is None:
                confirmation_traits = [
                    Intercooler(
                        request_method='POST',
                        redirect_after=request.url
                    )
                ]

                next_in_queue = window.next_submission

                if next_in_queue and next_in_queue is not self.submission:
                    confirmation_traits.append(Confirm(
                        _(
                            "This is not the oldest undecided submission of "
                            "this registration window. Do you really want to "
                            "confirm this submission?"
                        ),
                        _(
                            "By confirming this submission, you will prefer "
                            "this over a submission that came in earlier."
                        ),
                        _(
                            "Confirm registration"
                        ),
                        _(
                            "Cancel"
                        )
                    ))

                links.append(
                    Link(
                        text=_("Confirm registration"),
                        url=request.return_here(
                            layout.csrf_protected_url(
                                request.link(
                                    self.submission, 'confirm-registration')
                            )
                        ),
                        attrs={'class': 'accept-link'},
                        traits=confirmation_traits
                    )
                )
                extra.append(
                    Link(
                        text=_("Deny registration"),
                        url=request.return_here(
                            layout.csrf_protected_url(
                                request.link(
                                    self.submission, 'deny-registration')
                            )
                        ),
                        attrs={'class': 'delete-link'},
                        traits=(
                            Intercooler(
                                request_method='POST',
                                redirect_after=request.url
                            ),
                        )
                    )
                )

            # a registration was accepted before, we can issue an uninvite
            if self.submission.spots and self.submission.claimed:
                links.append(
                    Link(
                        text=_("Cancel registration"),
                        url=request.return_here(
                            layout.csrf_protected_url(
                                request.link(
                                    self.submission, 'cancel-registration')
                            )
                        ),
                        attrs={'class': 'delete-link'},
                        traits=(
                            Intercooler(
                                request_method='POST',
                                redirect_after=request.url
                            ),
                        )
                    )
                )
            extra.append(
                Link(
                    text=_("Registration Window"),
                    url=request.link(window),
                    attrs={'class': 'edit-link'}
                )
            )

        edit_link = URL(request.link(self.submission))
        edit_link = edit_link.query_param('edit', '').as_string()

        (links if not links else extra).append(
            Link(
                text=_('Edit submission'),
                url=request.return_here(edit_link),
                attrs={'class': 'edit-link'}
            )
        )

        if extra:
            links.append(LinkGroup(
                _("Advanced"),
                links=extra,
                right_side=False
            ))

        return links


@handlers.registered_handler('RSV')
class ReservationHandler(Handler, TicketDeletionMixin):

    handler_title = _("Reservations")
    code_title = _("Reservations")

    @cached_property
    def resource(self):
        if self.deleted:
            return None
        query = self.session.query(Resource)
        query = query.filter(Resource.id == self.reservations[0].resource)

        return query.one()

    @cached_property
    def reservations(self):
        # libres allows for multiple reservations with a single request (token)
        # for now we don't really have that case in onegov.org, but we
        # try to be aware of it as much as possible
        query = self.session.query(Reservation)
        query = query.filter(Reservation.token == self.id)
        query = query.order_by(Reservation.start)

        return tuple(query)

    @cached_property
    def submission(self):
        return FormSubmissionCollection(self.session).by_id(self.id)

    @property
    def payment(self):
        return self.reservations and self.reservations[0].payment

    @property
    def deleted(self):
        return False if self.reservations else True

    @property
    def extra_data(self):
        return self.submission and [
            v for v in self.submission.data.values()
            if isinstance(v, str)
        ]

    @property
    def email(self):
        # the e-mail is the same over all reservations
        if self.deleted:
            return self.ticket.snapshot.get('email')
        return self.reservations[0].email

    @property
    def undecided(self):
        # if there is no reservation with an 'accept' marker, the user
        # has not yet made a decision
        if self.deleted:
            return False

        for r in self.reservations:
            if r.data and r.data.get('accepted'):
                return False

        return True

    @property
    def title(self):
        parts = []

        for ix, reservation in enumerate(self.reservations):
            parts.append(self.get_reservation_title(reservation))

            if ix == 4:
                parts.append('…')
                break

        return ', '.join(parts)

    def get_reservation_title(self, reservation):
        return self.resource.reservation_title(reservation)

    @property
    def subtitle(self):
        if self.submission:
            return ', '.join(
                p for p in (self.email, self.submission.title) if p)
        elif self.reservations:
            return self.email
        else:
            return None

    @property
    def group(self):
        return self.resource.title if self.resource else None

    @classmethod
    def handle_extra_parameters(cls, session, query, extra_parameters):
        if 'allocation_id' in extra_parameters:
            allocations = session.query(Allocation.group)
            allocations = allocations.filter(
                Allocation.id == int(extra_parameters['allocation_id']))

            tokens = session.query(Reservation.token)
            tokens = tokens.filter(
                Reservation.target.in_(allocations.subquery()))

            handler_ids = tuple(t[0].hex for t in tokens)

            if handler_ids:
                query = query.filter(Ticket.handler_id.in_(handler_ids))
            else:
                query = query.filter(False)

        return query

    def get_summary(self, request):
        layout = DefaultLayout(self.resource, request)

        parts = []
        parts.append(
            render_macro(layout.macros['reservations'], request, {
                'reservations': self.reservations,
                'layout': layout
            })
        )

        if self.submission:
            form = self.submission.form_class(data=self.submission.data)

            parts.append(
                render_macro(layout.macros['display_form'], request, {
                    'form': form,
                    'layout': layout
                })
            )

        return ''.join(parts)

    def get_links(self, request):

        if self.deleted:
            return []

        links = []

        accepted = tuple(
            r.data and r.data.get('accepted') or False
            for r in self.reservations
        )

        if not all(accepted):
            links.append(
                Link(
                    text=_("Accept all reservations"),
                    url=request.return_here(
                        request.link(self.reservations[0], 'accept')
                    ),
                    attrs={'class': 'accept-link'}
                )
            )

        advanced_links = []

        if self.submission:
            link = URL(request.link(self.submission))
            link = link.query_param('edit', '')
            link = link.query_param('title', request.translate(
                _("Details about the reservation")))
            link = request.return_here(link.as_string())

            advanced_links.append(
                Link(
                    text=_('Edit details'),
                    url=link,
                    attrs={'class': ('edit-link', 'border')}
                )
            )

        advanced_links.append(Link(
            text=_("Reject all"),
            url=request.return_here(
                request.link(self.reservations[0], 'reject')
            ),
            attrs={'class': 'delete-link'},
            traits=(
                Confirm(
                    _("Do you really want to reject all reservations?"),
                    _("Rejecting these reservations can't be undone."),
                    _("Reject reservations"),
                    _("Cancel")
                ),
                Intercooler(
                    request_method='GET',
                    redirect_after=request.url
                )
            )
        ))

        for reservation in self.reservations:
            link = URL(request.link(reservation, 'reject'))
            link = link.query_param('reservation-id', reservation.id)
            link = request.return_here(link.as_string())

            title = self.get_reservation_title(reservation)
            advanced_links.append(Link(
                text=_("Reject ${title}", mapping={'title': title}),
                url=link,
                attrs={'class': 'delete-link'},
                traits=(
                    Confirm(
                        _("Do you really want to reject this reservation?"),
                        _("Rejecting ${title} can't be undone.", mapping={
                            'title': title
                        }),
                        _("Reject reservation"),
                        _("Cancel")
                    ),
                    Intercooler(
                        request_method='GET',
                        redirect_after=request.url
                    )
                )
            ))

        links.append(LinkGroup(
            _("Advanced"),
            links=advanced_links,
            right_side=False
        ))

        return links


@handlers.registered_handler('EVN')
class EventSubmissionHandler(Handler, TicketDeletionMixin):

    handler_title = _("Events")
    code_title = _("Events")

    @cached_property
    def collection(self):
        return EventCollection(self.session)

    @cached_property
    def event(self):
        return self.collection.by_id(self.id)

    @property
    def deleted(self):
        return self.event is None

    @cached_property
    def source(self):
        # values stored only when importing with cli
        return self.data.get('source')

    @cached_property
    def import_user(self):
        # values stored only when importing with cli
        return self.data.get('user')

    @cached_property
    def email(self):
        return self.event and self.event.meta.get('submitter_email')

    @property
    def title(self):
        return self.event.title

    @property
    def subtitle(self):
        if self.deleted:
            return None

        parts = (
            self.event.meta.get('submitter_email'),
            '{:%d.%m.%Y %H:%M}'.format(self.event.localized_start)
        )

        return ', '.join(p for p in parts if p)

    @property
    def extra_data(self):
        return [
            self.event.description,
            self.event.title,
            self.event.location
        ]

    @property
    def undecided(self):
        return self.event and self.event.state == 'submitted'

    @cached_property
    def group(self):
        return _("Event")

    def get_summary(self, request):
        layout = EventLayout(self.event, request)
        return render_macro(layout.macros['display_event'], request, {
            'event': self.event,
            'layout': layout
        })

    def get_links(self, request):

        links = []
        layout = EventLayout(self.event, request)

        if self.event and self.event.state == 'submitted':
            links.append(Link(
                text=_("Accept event"),
                url=request.return_here(request.link(self.event, 'publish')),
                attrs={'class': 'accept-link'},
            ))
        if not self.event:
            return links

        advanced_links = [
            Link(
                text=_('Edit event'),
                url=request.return_here(request.link(self.event, 'edit')),
                attrs={'class': ('edit-link', 'border')}
            )]

        if not self.event.source:
            advanced_links.append(
                Link(
                    text=_("Reject event"),
                    url=layout.csrf_protected_url(
                        request.link(self.event)),
                    attrs={'class': ('delete-link')},
                    traits=(
                        Confirm(
                            _("Do you really want to reject this event?"),
                            _("Rejecting this event can't be undone."),
                            _("Reject event"),
                            _("Cancel")
                        ),
                        Intercooler(
                            request_method='DELETE',
                            redirect_after=request.link(self.ticket)
                        )
                    )
                )
            )

        elif self.event.state in ('published', 'submitted'):
            advanced_links.append(
                Link(
                    text=_("Withdraw event"),
                    url=layout.csrf_protected_url(request.link(
                        self.event, name='withdraw')),
                    attrs={'class': ('delete-link')},
                    traits=(
                        Confirm(
                            _("Do you really want to withdraw this event?"),
                            _("You can re-publish an imported event later."),
                            _("Withdraw event"),
                            _("Cancel")
                        ),
                        Intercooler(
                            request_method='POST',
                            redirect_after=request.link(self.ticket)
                        )
                    )
                )
            )

        elif self.event.state == 'withdrawn':
            advanced_links.append(
                Link(
                    text=_("Re-publish event"),
                    url=request.return_here(
                        request.link(self.event, 'publish')),
                    attrs={'class': 'accept-link'}
                )
            )

        links.append(LinkGroup(_("Advanced"), links=advanced_links,
                               right_side=False))

        return links


@handlers.registered_handler('DIR')
class DirectoryEntryHandler(Handler, TicketDeletionMixin):

    handler_title = _("Directory Entry Submissions")
    code_title = _("Directory Entry Submissions")

    @cached_property
    def collection(self):
        return FormSubmissionCollection(self.session)

    @cached_property
    def submission(self):
        return self.collection.by_id(self.id)

    @cached_property
    def form(self):
        return self.submission.form_class(data=self.submission.data)

    @cached_property
    def directory(self):
        if self.submission:
            directory_id = self.submission.meta['directory']
        else:
            directory_id = self.ticket.handler_data['directory']

        return self.session.query(Directory).filter_by(id=directory_id).first()

    @cached_property
    def entry(self):
        if self.submission:
            id = self.submission.meta.get('directory_entry')
        else:
            id = self.ticket.handler_data.get('directory_entry')

        return self.session.query(DirectoryEntry).filter_by(id=id).first()

    @property
    def deleted(self):
        if not self.directory:
            return True

        if self.kind == 'change-request':
            if self.submission:
                data = self.submission.meta
            else:
                data = self.ticket.handler_data

            entry = self.session.query(DirectoryEntry)\
                .filter_by(id=data['directory_entry'])\
                .first()

            if not entry:
                return True

        if self.state == 'adopted':
            name = self.ticket.handler_data.get('entry_name')
            return not self.directory.entry_with_name_exists(name)

        return False

    @property
    def email(self):
        return self.submission.email

    @property
    def submitter_name(self):
        return self.deleted and self.ticket.snapshot.get('submitter_name') \
            or self.submission.submitter_name

    @property
    def submitter_phone(self):
        return self.deleted and self.ticket.snapshot.get('submitter_phone') \
            or self.submission.submitter_phone

    @property
    def submitter_address(self):
        return self.deleted and self.ticket.snapshot.get('submitter_address') \
            or self.submission.submitter_address

    @property
    def title(self):
        return self.submission.title

    @property
    def subtitle(self):
        return None

    @property
    def group(self):
        return self.directory.title

    @property
    def payment(self):
        return self.submission and self.submission.payment

    @property
    def state(self):
        return self.ticket.handler_data.get('state')

    @property
    def extra_data(self):
        return self.submission and [
            v for v in self.submission.data.values()
            if isinstance(v, str)
        ]

    @property
    def undecided(self):
        if not self.directory or self.deleted:
            return False

        return self.state is None

    @property
    def kind(self):
        if self.submission:
            data = self.submission.meta
        else:
            data = self.ticket.handler_data

        if 'change-request' in data.get('extensions', ()):
            return 'change-request'
        else:
            return 'new-entry'

    def get_summary(self, request):
        layout = DefaultLayout(self.submission, request)

        # XXX this is a poor man's request.get_form
        self.form.request = request
        self.form.model = self.submission

        macro = layout.macros['directory_entry_submission']

        return render_macro(macro, request, {
            'form': self.form,
            'layout': layout,
            'handler': self,
        })

    def get_links(self, request):

        links = []

        if not self.directory or self.deleted:
            return links

        if self.state is None:
            links.append(
                Link(
                    text=_("Adopt"),
                    url=request.link(
                        self.directory.submission_action(
                            'adopt', self.submission.id
                        )
                    ),
                    attrs={'class': 'accept-link'},
                    traits=(
                        Intercooler(
                            request_method='POST',
                            redirect_after=request.url
                        ),
                    )
                )
            )

        if self.state == 'adopted':
            links.append(
                Link(
                    text=_("View directory entry"),
                    url=request.class_link(DirectoryEntry, {
                        'directory_name': self.directory.name,
                        'name': self.ticket.handler_data['entry_name']
                    }),
                    attrs={'class': 'view-link'},
                )
            )

        advanced_links = []

        if self.state is None:
            link = URL(request.link(self.submission))
            link = link.query_param('edit', '')
            link = link.query_param('title', request.translate(
                _("Edit details")))
            link = request.return_here(link.as_string())

            advanced_links.append(
                Link(
                    text=_('Edit details'),
                    url=link,
                    attrs={'class': ('edit-link', 'border')}
                )
            )

            advanced_links.append(Link(
                text=_("Reject"),
                url=request.link(
                    self.directory.submission_action(
                        'reject', self.submission.id
                    )
                ),
                attrs={'class': 'delete-link'},
                traits=(
                    Confirm(
                        _("Do you really want to reject this entry?"),
                        _("This cannot be undone."),
                        _("Reject entry"),
                        _("Cancel")
                    ),
                    Intercooler(
                        request_method='POST',
                        redirect_after=request.url
                    )
                )
            ))

        links.append(LinkGroup(
            _("Advanced"),
            links=advanced_links,
            right_side=False
        ))

        return links
