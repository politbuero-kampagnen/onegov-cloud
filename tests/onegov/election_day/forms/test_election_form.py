from datetime import date
from onegov.ballot import Election
from onegov.election_day.forms import ElectionForm
from onegov.election_day.models import Canton
from onegov.election_day.models import Municipality
from tests.onegov.election_day.common import DummyRequest
from wtforms.validators import InputRequired


def test_election_form_domains():
    form = ElectionForm()
    assert ElectionForm().domain.choices is None

    form.set_domain(Canton(name='be', canton='be'))
    assert sorted(form.domain.choices) == [
        ('canton', 'Cantonal'),
        ('federation', 'Federal'),
        ('region', 'Regional'),
    ]

    form.set_domain(Municipality(name='bern', municipality='351'))
    assert sorted(form.domain.choices) == [
        ('canton', 'Cantonal'),
        ('federation', 'Federal'),
        ('municipality', 'Communal')
    ]


def test_election_form_translations(session):
    form = ElectionForm()
    form.request = DummyRequest(session=session)
    form.request.default_locale = 'de_CH'
    form.on_request()
    assert isinstance(form.election_de.validators[0], InputRequired)
    assert form.election_fr.validators == []
    assert form.election_it.validators == []
    assert form.election_rm.validators == []

    form = ElectionForm()
    form.request = DummyRequest(session=session)
    form.request.default_locale = 'fr_CH'
    form.on_request()
    assert form.election_de.validators == []
    assert isinstance(form.election_fr.validators[0], InputRequired)
    assert form.election_it.validators == []
    assert form.election_rm.validators == []


def test_election_form_model(session, related_link_labels):
    model = Election()
    model.title = 'Election (DE)'
    model.title_translations['de_CH'] = 'Election (DE)'
    model.title_translations['fr_CH'] = 'Election (FR)'
    model.title_translations['it_CH'] = 'Election (IT)'
    model.title_translations['rm_CH'] = 'Election (RM)'
    model.date = date.today()
    model.domain = 'federation'
    model.shortcode = 'xy'
    model.type = 'proporz'
    model.majority_type = 'relative'
    model.number_of_mandates = 5
    model.related_link = 'http://u.rl'
    model.related_link_label = related_link_labels
    model.tacit = False
    model.distinct = False
    model.expats = False
    model.after_pukelsheim = True
    model.colors = {
        'FDP': '#3a8bc1',
        'CVP': '#ff9100',
    }

    form = ElectionForm()
    form.apply_model(model)
    form.request = DummyRequest(session=session)

    assert form.election_de.data == 'Election (DE)'
    assert form.election_fr.data == 'Election (FR)'
    assert form.election_it.data == 'Election (IT)'
    assert form.election_rm.data == 'Election (RM)'
    assert form.date.data == date.today()
    assert form.domain.data == 'federation'
    assert form.shortcode.data == 'xy'
    assert form.election_type.data == 'proporz'
    assert form.mandates.data == 5
    assert form.related_link.data == 'http://u.rl'
    assert form.related_link_label_de.data == 'DE'
    assert form.related_link_label_fr.data == 'FR'
    assert form.related_link_label_it.data == 'IT'
    assert form.related_link_label_rm.data == 'RM'
    assert form.tacit.data is False
    assert form.distinct.data is False
    assert form.expats.data is False
    assert form.after_pukelsheim.data is True
    assert form.colors.data == (
        'CVP #ff9100\n'
        'FDP #3a8bc1'
    )

    form.election_de.data = 'An Election (DE)'
    form.election_fr.data = 'An Election (FR)'
    form.election_it.data = 'An Election (IT)'
    form.election_rm.data = 'An Election (RM)'
    form.date.data = date(2016, 1, 1)
    form.domain.data = 'canton'
    form.shortcode.data = 'yz'
    form.election_type.data = 'majorz'
    form.mandates.data = 2
    form.majority_type.data = 'absolute'
    form.absolute_majority.data = 10000
    form.related_link.data = 'http://ur.l'
    form.tacit.data = True
    form.distinct.data = True
    form.expats.data = True
    form.after_pukelsheim.data = False
    form.colors.data = (
        'CVP #ff9100\r\n'
        'SP Juso #dd0e0e\n'
        'FDP   #3a8bc1\n'
        'GLP\t\t#aeca00\n'
    )
    form.update_model(model)

    assert model.title == 'An Election (DE)'
    assert model.title_translations['de_CH'] == 'An Election (DE)'
    assert model.title_translations['fr_CH'] == 'An Election (FR)'
    assert model.title_translations['it_CH'] == 'An Election (IT)'
    assert model.title_translations['rm_CH'] == 'An Election (RM)'
    assert model.date == date(2016, 1, 1)
    assert model.domain == 'canton'
    assert model.shortcode == 'yz'
    assert model.type == 'majorz'
    assert model.number_of_mandates == 2
    assert model.majority_type == 'absolute'
    assert model.absolute_majority == 10000
    assert model.related_link == 'http://ur.l'
    assert model.tacit is True
    assert model.distinct is True
    assert model.expats is True
    assert model.after_pukelsheim is False
    assert model.colors == {
        'CVP': '#ff9100',
        'FDP': '#3a8bc1',
        'GLP': '#aeca00',
        'SP Juso': '#dd0e0e',
    }


def test_election_form_relations(session):
    session.add(
        Election(
            title="First Election",
            domain='federation',
            date=date(2011, 1, 1),
        )
    )
    session.add(
        Election(
            title="Second Election",
            domain='federation',
            date=date(2011, 1, 2),
        )
    )

    # Add a new election with relations
    election = Election()

    form = ElectionForm()
    form.request = DummyRequest(session=session)
    form.on_request()
    assert form.related_elections.choices == [
        ('second-election', '02.01.2011 Second Election'),
        ('first-election', '01.01.2011 First Election'),
    ]

    form.election_de.data = 'Third Election'
    form.date.data = date(2011, 1, 3)
    form.domain.data = 'federation'
    form.mandates.data = 1
    form.shortcode.data = 'SC'
    form.related_elections.data = ['first-election', 'second-election']
    form.update_model(election)
    session.add(election)
    session.flush()

    # Change existing relations of an election
    election = session.query(Election).filter_by(id='first-election').one()

    form = ElectionForm()
    form.request = DummyRequest(session=session)
    form.on_request()
    assert form.related_elections.choices == [
        ('third-election', '03.01.2011 SC Third Election'),
        ('second-election', '02.01.2011 Second Election'),
        ('first-election', '01.01.2011 First Election'),
    ]
    form.apply_model(election)
    assert form.related_elections.data == ['third-election']

    form.related_elections.data = ['second-election']
    form.update_model(election)
    session.add(election)
    session.flush()

    # Check all relations
    election = session.query(Election).filter_by(id='first-election').one()
    form.apply_model(election)
    assert form.related_elections.data == ['second-election']

    election = session.query(Election).filter_by(id='second-election').one()
    form.apply_model(election)
    assert set(form.related_elections.data) == set(
        ['first-election', 'third-election']
    )

    election = session.query(Election).filter_by(id='third-election').one()
    form.apply_model(election)
    assert form.related_elections.data == ['second-election']
