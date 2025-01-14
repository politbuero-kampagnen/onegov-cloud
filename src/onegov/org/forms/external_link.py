from onegov.org import _
from onegov.form import Form
from wtforms import StringField, TextAreaField, SelectField
from wtforms.fields.html5 import URLField
from wtforms.validators import InputRequired

from onegov.org.models.external_link import ExternalLinkCollection


class ExternalLinkForm(Form):

    title = StringField(
        label=_("Title"),
        validators=[InputRequired()])

    lead = TextAreaField(
        label=_("Lead"),
        description=_("Describes briefly what this entry is about"),
        validators=[InputRequired()],
        render_kw={'rows': 4})

    url = URLField(
        label=_("URL"),
        description=_("Url pointing to another website"),
        validators=[InputRequired()]
    )

    group = StringField(
        label=_("Group"),
        description=_("Used to group this link in the overview")
    )

    member_of = SelectField(
        label=_("Name of the list view this link will be shown"),
        choices=[]
    )

    def on_request(self):
        self.member_of.choices = [
            (id_, self.request.translate(_(name)))
            for id_, name in ExternalLinkCollection.form_choices()
        ]
