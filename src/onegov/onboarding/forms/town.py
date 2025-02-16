import re

from onegov.form import Form
from onegov.onboarding import _
from wtforms import StringField, validators
from wtforms.fields.html5 import EmailField
from wtforms_components import ColorField


class TownForm(Form):
    """ First step when starting a new town. """

    # the name is limited to 63 characters because it has to fit into a
    # subdomain which may not exceed that length
    name = StringField(
        label=_("Town Name"),
        description=_("The name of your town (real or fictitious)"),
        validators=[validators.InputRequired(), validators.Length(max=63)],
        render_kw={
            'autofocus': '',
            'class_': 'autocomplete',
            'data-source': 'town-names'
        }
    )

    user = EmailField(
        label=_("E-Mail"),
        description=_("Your e-mail address"),
        validators=[validators.InputRequired(), validators.Email()]
    )

    color = ColorField(
        label=_("Primary Color"),
        validators=[validators.InputRequired()],
        default='#005ba1'
    )

    def ensure_valid_name(self):
        name = self.name.data
        if not re.match(r'^[A-Za-z\s]+$', name) or not name.strip():
            self.name.errors.append(
                _("Only characters are allowed")
            )
            return False


class FinishForm(Form):
    pass
