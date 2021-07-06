import morepath

from onegov.core.security import Private, Public
from onegov.core.utils import normalize_for_url
from onegov.form import FormCollection, FormDefinition
from onegov.org import _, OrgApp
from onegov.org.elements import Link
from onegov.org.forms import FormDefinitionForm
from onegov.org.layout import FormEditorLayout, FormSubmissionLayout
from onegov.org.models import CustomFormDefinition
from webob import exc


def get_form_class(model, request):

    if isinstance(model, FormCollection):
        model = CustomFormDefinition()

    form_classes = {
        'builtin': FormDefinitionForm,
        'custom': FormDefinitionForm
    }

    return model.with_content_extensions(form_classes[model.type], request)


def get_hints(layout, window):
    if not window:
        return

    if window.in_the_past:
        yield 'stop', _("The registration has ended")
    elif not window.enabled:
        yield 'stop', _("The registration is closed")

    if window.enabled and window.in_the_future:
        yield 'date', _("The registration opens on ${day}, ${date}", mapping={
            'day': layout.format_date(window.start, 'weekday_long'),
            'date': layout.format_date(window.start, 'date_long')
        })

    if window.enabled and window.in_the_present:
        yield 'date', _("The registration closes on ${day}, ${date}", mapping={
            'day': layout.format_date(window.end, 'weekday_long'),
            'date': layout.format_date(window.end, 'date_long')
        })

        if window.limit and window.overflow:
            yield 'count', _("There's a limit of ${count} attendees", mapping={
                'count': window.limit
            })

        if window.limit and not window.overflow:
            spots = window.available_spots

            if spots == 0:
                yield 'stop', _("There are no spots left")
            elif spots == 1:
                yield 'count', _("There is one spot left")
            else:
                yield 'count', _("There are ${count} spots left", mapping={
                    'count': spots
                })


@OrgApp.form(
    model=FormDefinition,
    template='form.pt', permission=Public,
    form=lambda self, request: self.form_class
)
def handle_defined_form(self, request, form, layout=None):
    """ Renders the empty form and takes input, even if it's not valid, stores
    it as a pending submission and redirects the user to the view that handles
    pending submissions.

    """

    collection = FormCollection(request.session)

    if not self.current_registration_window:
        spots = 0
        enabled = True
    else:
        spots = 1
        enabled = self.current_registration_window.accepts_submissions(spots)

    if enabled and request.POST:
        submission = collection.submissions.add(
            self.name, form, state='pending', spots=spots)

        return morepath.redirect(request.link(submission))

    layout = layout or FormSubmissionLayout(self, request)

    return {
        'layout': layout,
        'title': self.title,
        'form': enabled and form,
        'definition': self,
        'form_width': 'small',
        'lead': layout.linkify(self.meta.get('lead')),
        'text': self.content.get('text'),
        'people': self.people,
        'contact': self.contact_html,
        'coordinates': self.coordinates,
        'hints': tuple(get_hints(layout, self.current_registration_window)),
        'hints_callout': not enabled,
        'button_text': _('Continue')
    }


@OrgApp.form(model=FormCollection, name='new', template='form.pt',
             permission=Private, form=get_form_class)
def handle_new_definition(self, request, form, layout=None):

    if form.submitted(request):

        if self.definitions.by_name(normalize_for_url(form.title.data)):
            request.alert(_("A form with this name already exists"))
        else:
            definition = self.definitions.add(
                title=form.title.data,
                definition=form.definition.data,
                type='custom'
            )
            form.populate_obj(definition)

            request.success(_("Added a new form"))
            return morepath.redirect(request.link(definition))

    layout = layout or FormEditorLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Forms"), request.link(self)),
        Link(_("New Form"), request.link(self, name='new'))
    ]

    return {
        'layout': layout,
        'title': _("New Form"),
        'form': form,
        'form_width': 'large',
    }


@OrgApp.form(model=FormDefinition, template='form.pt', permission=Private,
             form=get_form_class, name='edit')
def handle_edit_definition(self, request, form, layout=None):

    if form.submitted(request):
        form.populate_obj(self, exclude={'definition'})
        self.definition = form.definition.data

        request.success(_("Your changes were saved"))
        return morepath.redirect(request.link(self))
    elif not request.POST:
        form.process(obj=self)

    collection = FormCollection(request.session)

    layout = layout or FormEditorLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Forms"), request.link(collection)),
        Link(self.title, request.link(self)),
        Link(_("Edit"), request.link(self, name='edit'))
    ]

    return {
        'layout': layout,
        'title': self.title,
        'form': form,
        'form_width': 'large',
    }


@OrgApp.view(model=FormDefinition, request_method='DELETE',
             permission=Private)
def delete_form_definition(self, request):

    request.assert_valid_csrf_token()

    if self.type != 'custom':
        raise exc.HTTPMethodNotAllowed()

    if self.has_submissions(with_state='complete'):
        raise exc.HTTPMethodNotAllowed()

    FormCollection(request.session).definitions.delete(
        self.name, with_submissions=False, with_registration_windows=True)
