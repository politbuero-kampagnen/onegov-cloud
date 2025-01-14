from datetime import date
from onegov.ballot import Election
from onegov.ballot import ElectionAssociation
from onegov.election_day import _
from onegov.election_day.layouts import DefaultLayout
from onegov.form import Form
from onegov.form.fields import ChosenSelectMultipleField
from onegov.form.fields import PanelField
from re import findall
from sqlalchemy import or_
from wtforms import BooleanField
from wtforms import IntegerField
from wtforms import RadioField
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import ValidationError
from wtforms.fields.html5 import DateField
from wtforms.fields.html5 import URLField
from wtforms.validators import InputRequired
from wtforms.validators import NumberRange
from wtforms.validators import Optional


class ElectionForm(Form):

    election_type = RadioField(
        label=_("System"),
        choices=[
            ('majorz', _("Election based on the simple majority system")),
            ('proporz', _("Election based on proportional representation")),
        ],
        validators=[
            InputRequired()
        ],
        default='majorz'
    )

    majority_type = RadioField(
        label=_("Majority Type"),
        choices=[
            ('absolute', _("Absolute")),
            ('relative', _("Relative")),
        ],
        default='absolute',
        validators=[
            InputRequired()
        ],
        depends_on=('election_type', 'majorz'),
    )

    absolute_majority = IntegerField(
        label=_("Absolute majority"),
        validators=[
            Optional(),
            NumberRange(min=1)
        ],
        depends_on=('majority_type', 'absolute', 'election_type', 'majorz'),
    )

    domain = RadioField(
        label=_("Type"),
        validators=[
            InputRequired()
        ]
    )

    tacit = BooleanField(
        label=_("Tacit election"),
        render_kw=dict(force_simple=True)
    )

    expats = BooleanField(
        label=_("Expats"),
        description=_("The election contains seperate results for expats."),
        render_kw=dict(force_simple=True)
    )

    distinct = BooleanField(
        label=_("Distinct district"),
        description=_("The election contains results of a whole district."),
        render_kw=dict(force_simple=True),
        depends_on=('domain', 'region'),
    )

    after_pukelsheim = BooleanField(
        label=_("Doppelter Pukelsheim"),
        depends_on=('election_type', 'proporz'),
        render_kw=dict(force_simple=True)
    )

    date = DateField(
        label=_("Date"),
        validators=[
            InputRequired()
        ],
        default=date.today
    )

    mandates = IntegerField(
        label=_("Mandates / Seats"),
        validators=[
            InputRequired(),
            NumberRange(min=1)
        ]
    )

    shortcode = StringField(
        label=_("Shortcode")
    )

    election_de = StringField(
        label=_("German"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'de'}
    )
    election_fr = StringField(
        label=_("French"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'fr'}
    )
    election_it = StringField(
        label=_("Italian"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'it'}
    )
    election_rm = StringField(
        label=_("Romansh"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'rm'}
    )

    related_elections = ChosenSelectMultipleField(
        label=_("Related elections"),
        choices=[]
    )

    related_link = URLField(
        label=_("Link"),
        fieldset=_("Related link")
    )

    related_link_label_de = StringField(
        label=_("Link label german"),
        fieldset=_("Related link"),
        render_kw={'lang': 'de'}
    )
    related_link_label_fr = StringField(
        label=_("Link label french"),
        fieldset=_("Related link"),
        render_kw={'lang': 'fr'}
    )
    related_link_label_it = StringField(
        label=_("Link label italian"),
        fieldset=_("Related link"),
        render_kw={'lang': 'it'}
    )
    related_link_label_rm = StringField(
        label=_("Link label romansh"),
        fieldset=_("Related link"),
        render_kw={'lang': 'rm'}
    )

    color_hint = PanelField(
        label=_('Color suggestions'),
        text=(
            'AL #a74c97\n'
            'BDP #a9cf00\n'
            'CVP #d28b00\n'
            'EDU #7f6b65\n'
            'EVP #e3c700\n'
            'FDP #0084c7\n'
            'GLP #aeca00\n'
            'GRÜNE #54ba00\n'
            'Piraten #333333\n'
            'SP #c31906\n'
            'SVP #408b3d\n'
        ),
        kind='',
    )

    colors = TextAreaField(
        label=_('Colors'),
        render_kw={'rows': 12},
        description=(

        )
    )

    def parse_colors(self, text):
        if not text:
            return {}
        result = {
            key.strip(): value
            for key, value in findall(r'(.+)\s+(\#[0-9a-fA-F]{6})', text)
        }
        if len(text.strip().splitlines()) != len(result):
            raise ValueError('Could not parse colors')
        return result

    def validate_colors(self, field):
        try:
            self.parse_colors(field.data)
        except Exception:
            raise ValidationError(_('Invalid color definitions'))

    def on_request(self):
        self.election_de.validators = []
        self.election_fr.validators = []
        self.election_it.validators = []
        self.election_rm.validators = []

        default_locale = self.request.default_locale
        if default_locale.startswith('de'):
            self.election_de.validators.append(InputRequired())
        if default_locale.startswith('fr'):
            self.election_fr.validators.append(InputRequired())
        if default_locale.startswith('it'):
            self.election_de.validators.append(InputRequired())
        if default_locale.startswith('rm'):
            self.election_de.validators.append(InputRequired())

        layout = DefaultLayout(None, self.request)

        query = self.request.session.query(Election)
        query = query.order_by(Election.date.desc(), Election.shortcode)
        self.related_elections.choices = [
            (
                election.id,
                "{} {} {}".format(
                    layout.format_date(election.date, 'date'),
                    election.shortcode or '',
                    election.title,
                ).strip().replace("  ", " ")
            ) for election in query
        ]

    def set_domain(self, principal):
        self.domain.choices = [
            (key, text) for key, text in principal.domains_election.items()
        ]

    def update_model(self, model):
        model.date = self.date.data
        model.domain = self.domain.data
        model.type = self.election_type.data
        model.shortcode = self.shortcode.data
        model.number_of_mandates = self.mandates.data
        model.majority_type = self.majority_type.data
        model.absolute_majority = self.absolute_majority.data or None
        model.related_link = self.related_link.data
        model.tacit = self.tacit.data
        model.expats = self.expats.data
        model.distinct = self.distinct.data
        model.after_pukelsheim = self.after_pukelsheim.data

        titles = {}
        if self.election_de.data:
            titles['de_CH'] = self.election_de.data
        if self.election_fr.data:
            titles['fr_CH'] = self.election_fr.data
        if self.election_it.data:
            titles['it_CH'] = self.election_it.data
        if self.election_rm.data:
            titles['rm_CH'] = self.election_rm.data
        model.title_translations = titles

        link_labels = {}
        if self.related_link_label_de.data:
            link_labels['de_CH'] = self.related_link_label_de.data
        if self.related_link_label_fr.data:
            link_labels['fr_CH'] = self.related_link_label_fr.data
        if self.related_link_label_it.data:
            link_labels['it_CH'] = self.related_link_label_it.data
        if self.related_link_label_rm.data:
            link_labels['rm_CH'] = self.related_link_label_rm.data
        model.related_link_label = link_labels

        model.colors = self.parse_colors(self.colors.data)

        # use symetric relationships
        session = self.request.session
        query = session.query(ElectionAssociation)
        query = query.filter(
            or_(
                ElectionAssociation.source_id == model.id,
                ElectionAssociation.target_id == model.id
            )
        )
        for association in query:
            session.delete(association)

        for id_ in self.related_elections.data:
            if not model.id:
                model.id = model.id_from_title(session)
            session.add(ElectionAssociation(source_id=model.id, target_id=id_))
            session.add(ElectionAssociation(source_id=id_, target_id=model.id))

    def apply_model(self, model):
        titles = model.title_translations or {}
        self.election_de.data = titles.get('de_CH')
        self.election_fr.data = titles.get('fr_CH')
        self.election_it.data = titles.get('it_CH')
        self.election_rm.data = titles.get('rm_CH')

        link_labels = model.related_link_label or {}
        self.related_link_label_de.data = link_labels.get('de_CH', '')
        self.related_link_label_fr.data = link_labels.get('fr_CH', '')
        self.related_link_label_it.data = link_labels.get('it_CH', '')
        self.related_link_label_rm.data = link_labels.get('rm_CH', '')

        self.date.data = model.date
        self.domain.data = model.domain
        self.shortcode.data = model.shortcode
        self.election_type.data = model.type
        self.mandates.data = model.number_of_mandates
        self.majority_type.data = model.majority_type
        self.absolute_majority.data = model.absolute_majority
        self.related_link.data = model.related_link
        self.tacit.data = model.tacit
        self.expats.data = model.expats
        self.distinct.data = model.distinct
        self.after_pukelsheim.data = model.after_pukelsheim

        self.colors.data = '\n'.join((
            f'{name} {model.colors[name]}' for name in sorted(model.colors)
        ))

        if model.type == 'majorz':
            self.election_type.choices = [
                ('majorz', _("Election based on the simple majority system"))
            ]
            self.election_type.data = 'majorz'

        else:
            self.election_type.choices = [
                ('proporz', _("Election based on proportional representation"))
            ]
            self.election_type.data = 'proporz'

        self.related_elections.choices = [
            choice for choice in self.related_elections.choices
            if choice[0] != model.id
        ]
        self.related_elections.data = [
            association.target_id for association in model.related_elections
        ]
