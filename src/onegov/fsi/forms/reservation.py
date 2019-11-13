from wtforms.validators import InputRequired
from onegov.form import Form
from onegov.form.fields import ChosenSelectField
from onegov.fsi.collections.attendee import CourseAttendeeCollection
from onegov.fsi.collections.course_event import CourseEventCollection
from onegov.fsi import _


class FsiReservationForm(Form):

    attendee_id = ChosenSelectField(
        label=_("Attendee"),
        choices=[],
        validators=[
            InputRequired()
        ]
    )

    course_event_id = ChosenSelectField(
        label=_("Course Event"),
        choices=[],
        validators=[
            InputRequired()
        ]
    )

    def on_request(self):
        """
        - self.model is the reservation_collection of the view using the form
        . the collection has the property course_event or attendee
        - in path.py, the attendee_id is set using the request if not a manager
        - self.model.attendee will be filled always if the user is not manager
        - if attendee is None, this is a placeholder reservation

        """
        attendee = self.model.attendee
        event = self.model.course_event
        attendee_collection = CourseAttendeeCollection(
            self.request.session, external_only=self.model.external_only)
        event_collection = CourseEventCollection(
            self.request.session, upcoming_only=True)

        event_choices = event_collection.query()

        def _repr(attendee):
            return f'{str(attendee)} - {attendee.email}'

        if self.request.view_name == 'add-placeholder':
            self.delete_field('attendee_id')

        elif attendee:
            self.attendee_id.choices = ((str(attendee.id), _repr(attendee)),)
            # Filter courses he registered
            event_choices = event_choices.filter(
                self.model.model_class.attendee_id != attendee.id)

        else:
            self.attendee_id.choices = list(
                (str(a.id), _repr(a)) for a in attendee_collection.query()
            )
            if not self.attendee_id.choices:
                self.attendee_id.choices.append(('', _('None')))

        if event:
            self.course_event_id.choices = ((str(event.id), event.name),)
        else:
            self.course_event_id.choices = list(
                (str(a.id), a.name) for a in event_choices
            )

