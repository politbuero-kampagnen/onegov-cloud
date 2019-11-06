from onegov.fsi import FsiApp
from onegov.fsi.collections.course_event import CourseEventCollection
from onegov.fsi.forms.course_event import CourseEventForm
from onegov.fsi import _
from onegov.fsi.layout import CourseLayout


@FsiApp.html(
    model=CourseEventCollection,
    template='course_events.pt')
def view_course_event_collection(self, request):
    layout = CourseLayout(self, request)
    return {
            'title': _('Courses Events'),
            'layout': layout,
            'model': self,
            'courses': self.query().all()
    }


@FsiApp.form(
    model=CourseEventCollection,
    template='form.pt',
    name='new',
    form=CourseEventForm
)
def view_create_course_event(self, request, form):
    layout = CourseLayout(self, request)

    if form.submitted(request):
        self.add(**form.get_useful_data())

        request.success(_("Added a new course event"))
        return request.redirect(request.link(self))

    return {
        'title': _('Add Course'),
        'layout': layout,
        'model': self,
        'form': form

    }
