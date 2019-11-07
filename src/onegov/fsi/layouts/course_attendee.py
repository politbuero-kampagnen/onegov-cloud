from cached_property import cached_property

from onegov.core.elements import Link, Confirm, Intercooler
from onegov.fsi.collections.attendee import CourseAttendeeCollection
from onegov.fsi.layout import DefaultLayout
from onegov.fsi import _


class CourseAttendeeLayout(DefaultLayout):

    @cached_property
    def title(self):
        if self.request.view_name == '':
            return _('Profile Details')
        if self.request.view_name == 'edit':
            return _('Edit Profile')

    @cached_property
    def breadcrumbs(self):
        return [Link(_('Personal Profile'))]

    @cached_property
    def editbar_links(self):
        if not self.request.is_manager:
            return []
        if self.request.view_name == '':
            return [
                Link(
                    _('Edit Profile'),
                    url=self.request.link(self.model, name='edit'),
                    attrs={'class': 'edit-icon'}
                )
            ]
        if self.request.view_name in ('add-external', 'edit'):
            return [
                Link(
                    _('Add External Attendee'),
                    url=self.request.class_link(
                        CourseAttendeeCollection, name='add-external'),
                    attrs={'class': 'plus-icon'}

                )
            ]

    @cached_property
    def salutation(self):
        return self.format_salutation(self.model.title)


class CourseAttendeeCollectionLayout(CourseAttendeeLayout):

    @cached_property
    def collection(self):
        return CourseAttendeeCollection(self.request.session)

    @cached_property
    def title(self):
        if self.request.view_name == 'add-external':
            return _('Add External Attendee')
        return _('Manage Course Attendees')

    @cached_property
    def editbar_links(self):
        return [
            Link(
                _('Add External Attendee'),
                url=self.request.class_link(
                    CourseAttendeeCollection, name='add-external'),
                attrs={'class': 'users'}
            ),
            Link(
                text=_("Add attendee from user"),
                url=self.request.link(
                    CourseAttendeeCollection(self.request.session),
                    name='add-from-user'),
                attrs={'class': 'copy-link'},
                traits=(
                    Confirm(
                        _("Do you really want to add a course attendee?"),
                        _("This is for development only!"),
                        _("Add Attendee"),
                        _("Cancel")
                    ),
                    Intercooler(
                        request_method='POST',
                        redirect_after=self.request.link(self.collection)
                    )
                )
            )
        ]

    @cached_property
    def breadcrumbs(self):
        if self.request.view_name == 'add-external':
            return [Link(_('Add External Attendee'))]
        else:
            return [Link(_('Personal Profile'))]
