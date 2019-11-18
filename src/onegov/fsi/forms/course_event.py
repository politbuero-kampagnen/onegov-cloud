import re
from collections import OrderedDict
from datetime import timedelta

from wtforms.widgets import TextInput

from onegov.core.utils import linkify
from onegov.form.fields import TimezoneDateTimeField, ChosenSelectField

from wtforms import StringField, IntegerField, BooleanField
from wtforms.validators import InputRequired

from onegov.form.fields import HtmlField
from onegov.fsi import _
from onegov.form import Form
from onegov.fsi.models.course_event import course_status_choices

mapping = OrderedDict({'year': 365, 'month': 30, 'week': 7, 'day': 1})


def string_to_timedelta(value):
    # Incoming model value
    if not value:
        return None

    pattern = r'(\d+)\.?\d?\s?(\w+)'
    g = re.search(pattern, value)
    if not isinstance(g, re.Match) or not g.group():
        return None
    count = g.group(1)
    unit = g.group(2)

    units = tuple(mapping.keys()) + tuple(f'{v}s' for v in mapping.keys())

    if unit in units:
        unit_ = unit[:-1] if unit[-1] == 's' else unit
        days = int(count) * mapping[unit_]
        return timedelta(days=days)
    else:
        raise AssertionError(f'unit {unit} not in allowed units')


def datetime_to_string(dt):
    if not dt or not isinstance(dt, timedelta):
        return None
    remaining = dt.days

    def s_append(key, value):
        return key + 's' if value >= 2 else key

    for unit, divisor in mapping.items():
        count = remaining // divisor
        if count != 0:
            return f"{count} {s_append(unit, count)}"
    return None


class IntervalStringField(StringField):
    """To handle incoming data from python, override process_data.
    Similarly, to handle incoming data from the outside,
    override process_formdata.

    The _value method is called by the TextInput widget to provide
     the value that is displayed in the form. Overriding the process_formdata()
    method processes the incoming form data back into a list of tags.

    """
    widget = TextInput()

    def process_data(self, value):
        print('test')
        super().process_data(value)

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            self.data = string_to_timedelta(valuelist[0].strip())
        else:
            self.data = None

    def _value(self):
        if self.data is not None:
            return datetime_to_string(self.data)
        else:
            return ''


class CourseEventForm(Form):

    # Course info
    name = StringField(
        label=_('Short Description'),
        validators=[
            InputRequired()
        ]
    )

    presenter_name = StringField(
        label=_('Presenter'),
        description=_('Full name of the presenter'),
        validators=[
            InputRequired()
        ]
    )

    presenter_company = StringField(
        label=_('Company'),
        description='Presenters company',
        validators=[
            InputRequired()
        ]
    )

    presenter_email = StringField(
        label=_('Presenter Email'),
        validators=[
            InputRequired()
        ]
    )

    description = HtmlField(
        label=_("Description"),
        render_kw={'rows': 10, 'cols': 8},
        validators=[
            InputRequired()
        ]
    )

    mandatory_refresh = BooleanField(
        label=_("Refresh mandatory"),
        default=False
    )

    hidden_from_public = BooleanField(
        label=_("Hidden"),
        default=False,
    )

    refresh_interval = IntervalStringField(
        label=_('Refresh Interval'),
        description=_('e.g. 5 years of 1 month a')
    )

    # Course Event info
    start = TimezoneDateTimeField(
        label=_('Course Start'),
        timezone='Europe/Zurich',
        validators=[
            InputRequired()
        ]
    )

    end = TimezoneDateTimeField(
        label=_('Course End'),
        timezone='Europe/Zurich',
        validators=[
            InputRequired()
        ]
    )

    min_attendees = IntegerField(
        label=_('Attendees min'),
        default=1
    )

    max_attendees = IntegerField(
        label=_('Attendees max'),
        validators=[
            InputRequired()
        ],
    )

    status = ChosenSelectField(
        label=_('Status'),
        choices=course_status_choices(),
        default='created'
    )

    def get_useful_data(self, exclude={'csrf_token'}):
        result = super().get_useful_data(exclude)
        if self.description.data:
            result['description'] = linkify(
                self.description.data, escape=False)
        return result

    def apply_model(self, model):
        self.name.data = model.name
        self.presenter_name.data = model.presenter_name
        self.presenter_company.data = model.presenter_company
        self.presenter_email.data = model.presenter_email
        self.description.data = model.description
        self.mandatory_refresh.data = model.mandatory_refresh
        self.hidden_from_public.data = model.hidden_from_public

        self.start.data = model.start
        self.end.data = model.end
        self.min_attendees.data = model.min_attendees
        self.max_attendees.data = model.max_attendees
        self.status.data = model.status
        self.refresh_interval.data = model.refresh_interval

    def update_model(self, model):
        model.name = self.name.data
        model.presenter_name = self.presenter_name.data
        model.presenter_company = self.presenter_company.data
        model.presenter_email = self.presenter_email.data
        model.description = linkify(self.description.data, escape=False)
        model.mandatory_refresh = self.mandatory_refresh.data
        model.hidden_from_public = self.hidden_from_public.data

        model.start = self.start.data
        model.end = self.end.data
        model.min_attendees = self.min_attendees.data
        model.max_attendees = self.max_attendees.data
        model.status = self.status.data
        model.refresh_interval = self.refresh_interval.data
        model.hidden_from_public = self.hidden_from_public.data
