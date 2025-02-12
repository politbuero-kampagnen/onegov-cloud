from datetime import date
from onegov.ballot import Election
from onegov.ballot import ElectionCompound
from onegov.ballot import ProporzElection
from onegov.election_day.forms import ElectionCompoundForm
from tests.onegov.election_day.common import DummyPostData
from tests.onegov.election_day.common import DummyRequest
from wtforms.validators import InputRequired


def test_election_compound_form_populate(session):
    form = ElectionCompoundForm()
    form.request = DummyRequest(session=session)

    form.on_request()
    assert form.elections.choices == []

    session.add(
        ProporzElection(
            title='election-1',
            domain='region',
            shortcode='2',
            date=date(2001, 1, 1))
    )
    session.add(
        Election(
            title='election-2',
            domain='region',
            shortcode='1',
            date=date(2001, 1, 1))
    )
    session.add(
        ProporzElection(
            title='election-3',
            domain='region',
            date=date(2000, 1, 1))
    )
    session.add(
        Election(
            title='election-4',
            domain='federation',
            date=date(2001, 1, 1))
    )
    session.flush()

    form.on_request()
    assert form.elections.choices == [
        ('election-1', '01.01.2001 2 election-1'),
        ('election-3', '01.01.2000 election-3'),
    ]


def test_election_compound_form_validate(session):
    session.add(
        ProporzElection(
            title='election-1',
            domain='region',
            date=date(2001, 1, 1))
    )
    session.add(
        ProporzElection(
            title='election-2',
            domain='region',
            date=date(2001, 1, 1))
    )
    session.flush()

    form = ElectionCompoundForm()
    form.request = DummyRequest(session=session)
    form.on_request()

    form.process(DummyPostData({
        'election_de': 'Elections',
        'domain': 'canton',
        'date': '2012-01-01',
        'elections': ['election-1'],
    }))
    assert form.validate()

    form.process(DummyPostData({
        'election_de': 'Elections',
        'domain': 'canton',
        'date': '2012-01-01',
        'elections': ['election-1', 'election-2'],
    }))
    assert form.validate()


def test_election_compound_form_translations(session):
    form = ElectionCompoundForm()
    form.request = DummyRequest(session=session)
    form.request.default_locale = 'de_CH'
    form.on_request()
    assert isinstance(form.election_de.validators[0], InputRequired)
    assert form.election_fr.validators == []
    assert form.election_it.validators == []
    assert form.election_rm.validators == []

    form = ElectionCompoundForm()
    form.request = DummyRequest(session=session)
    form.request.default_locale = 'fr_CH'
    form.on_request()
    assert form.election_de.validators == []
    assert isinstance(form.election_fr.validators[0], InputRequired)
    assert form.election_it.validators == []
    assert form.election_rm.validators == []


def test_election_compound_form_model(session, related_link_labels):
    date_ = date(2001, 1, 1)
    e1 = Election(domain='region', title='e', id='e-1', date=date_)
    e2 = Election(domain='region', title='e', id='e-2', date=date_)
    e3 = Election(domain='region', title='e', id='e-3', date=date_)
    session.add(e1)
    session.add(e2)
    session.add(e3)
    session.flush()

    model = ElectionCompound()
    model.title = 'Elections (DE)'
    model.title_translations['de_CH'] = 'Elections (DE)'
    model.title_translations['fr_CH'] = 'Elections (FR)'
    model.title_translations['it_CH'] = 'Elections (IT)'
    model.title_translations['rm_CH'] = 'Elections (RM)'
    model.date = date(2012, 1, 1)
    model.domain = 'canton'
    model.aggregated_by_entity = True
    model.shortcode = 'xy'
    model.related_link = 'http://u.rl'
    model.related_link_label = related_link_labels
    model.show_party_strengths = True
    model.show_mandate_allocation = True
    model.elections = [e1, e2]
    model.after_pukelsheim = True
    model.pukelsheim_completed = True
    model.colors = {
        'FDP': '#3a8bc1',
        'CVP': '#ff9100',
    }
    session.add(model)

    form = ElectionCompoundForm()
    form.apply_model(model)

    assert form.election_de.data == 'Elections (DE)'
    assert form.election_fr.data == 'Elections (FR)'
    assert form.election_it.data == 'Elections (IT)'
    assert form.election_rm.data == 'Elections (RM)'
    assert form.date.data == date(2012, 1, 1)
    assert form.domain.data == 'canton'
    assert form.aggregated_by_entity.data == True
    assert form.shortcode.data == 'xy'
    assert form.related_link.data == 'http://u.rl'
    assert form.related_link_label_de.data == 'DE'
    assert form.related_link_label_fr.data == 'FR'
    assert form.related_link_label_it.data == 'IT'
    assert form.related_link_label_rm.data == 'RM'
    assert form.show_party_strengths.data is True
    assert form.show_mandate_allocation.data is True
    assert form.elections.data == ['e-1', 'e-2']
    assert form.after_pukelsheim.data is True
    assert form.pukelsheim_completed.data is True
    assert form.colors.data == (
        'CVP #ff9100\n'
        'FDP #3a8bc1'
    )

    form.election_de.data = 'Some Elections (DE)'
    form.election_fr.data = 'Some Elections (FR)'
    form.election_it.data = 'Some Elections (IT)'
    form.election_rm.data = 'Some Elections (RM)'
    form.date.data = date(2016, 1, 1)
    form.domain.data = 'canton'
    form.aggregated_by_entity.data = False
    form.shortcode.data = 'yz'
    form.related_link.data = 'http://ur.l'
    form.show_party_strengths.data = False
    form.show_mandate_allocation.data = False
    form.elections.data = ['e-1', 'e-3', 'e-4']
    form.after_pukelsheim.data = False
    form.pukelsheim_completed.data = False
    form.colors.data = (
        'CVP #ff9100\r\n'
        'SP Juso #dd0e0e\n'
        'FDP   #3a8bc1\n'
        'GLP\t\t#aeca00\n'
    )

    form.request = DummyRequest(session=session)
    form.on_request()
    form.update_model(model)

    assert model.title == 'Some Elections (DE)'
    assert model.title_translations['de_CH'] == 'Some Elections (DE)'
    assert model.title_translations['fr_CH'] == 'Some Elections (FR)'
    assert model.title_translations['it_CH'] == 'Some Elections (IT)'
    assert model.title_translations['rm_CH'] == 'Some Elections (RM)'
    assert model.date == date(2016, 1, 1)
    assert model.domain == 'canton'
    assert model.aggregated_by_entity == False
    assert model.shortcode == 'yz'
    assert model.related_link == 'http://ur.l'
    assert model.pukelsheim_completed is False
    assert form.show_party_strengths.data is False
    assert form.show_mandate_allocation.data is False
    assert sorted([e.id for e in model.elections]) == ['e-1', 'e-3']
    assert model.colors == {
        'CVP': '#ff9100',
        'FDP': '#3a8bc1',
        'GLP': '#aeca00',
        'SP Juso': '#dd0e0e',
    }
