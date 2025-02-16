from datetime import date
from freezegun import freeze_time
from onegov.ballot import Election
from onegov.ballot import ElectionCompound
from onegov.ballot import ElectionResult
from onegov.ballot import PanachageResult
from onegov.ballot import PartyResult
from onegov.ballot import ProporzElection
from onegov.election_day.layouts import ElectionCompoundLayout
from tests.onegov.election_day.common import DummyRequest
from unittest.mock import Mock
import pytest


def test_election_compound_layout_1(session):
    date_ = date(2011, 1, 1)
    majorz = Election(title="majorz", domain='region', date=date_)
    proporz = ProporzElection(title="proporz", domain='region', date=date_)
    session.add(majorz)
    session.add(proporz)
    session.add(ElectionCompound(title="e", domain='canton', date=date_))
    session.flush()
    compound = session.query(ElectionCompound).one()
    request = DummyRequest()
    layout = ElectionCompoundLayout(compound, request)
    assert layout.all_tabs == (
        'lists',
        'districts',
        'candidates',
        'mandate-allocation',
        'party-strengths',
        'parties-panachage',
        'statistics',
        'data'
    )
    assert layout.title() == ''
    assert layout.title('undefined') == ''
    assert layout.title('districts') == '__districts'
    assert layout.title('candidates') == 'Elected candidates'
    assert layout.title('mandate-allocation') == 'Mandate allocation'
    assert layout.title('party-strengths') == 'Party strengths'
    assert layout.title('parties-panachage') == 'Panachage'
    assert layout.title('data') == 'Downloads'
    assert layout.title('statistics') == 'Election statistics'
    assert layout.main_view == 'ElectionCompound/districts'
    assert layout.majorz is False
    assert layout.proporz is False
    assert layout.has_party_results is False
    assert layout.tab_visible('statistics') is False
    assert request.app.principal.hidden_tabs == {'elections': ['lists']}
    assert layout.hide_tab('lists') is True

    request.app.principal.hidden_tabs = {}
    reloaded_layout = ElectionCompoundLayout(compound, request)
    assert reloaded_layout.hide_tab('lists') is False
    assert reloaded_layout.main_view == 'ElectionCompound/lists'

    compound.elections = [majorz]
    layout = ElectionCompoundLayout(compound, DummyRequest())
    assert layout.majorz is True
    assert layout.proporz is False

    compound.elections = [proporz]
    layout = ElectionCompoundLayout(compound, DummyRequest())
    assert layout.majorz is False
    assert layout.proporz is True

    compound.party_results.append(
        PartyResult(
            year=2017,
            number_of_mandates=0,
            votes=0,
            total_votes=100,
            name='A',
        )
    )
    assert layout.has_party_results is True

    with freeze_time("2014-01-01 12:00"):
        compound = ElectionCompound(
            title="ElectionCompound",
            domain='canton',
            date=date(2011, 1, 1),
        )
        session.add(compound)
        session.flush()
        ts = (
            '2ef359817c8f8a7354e201f891cd7c11a13f4e025aa25239c3ad0cabe58bc49b'
            '.1388577600'
        )

        request = DummyRequest()
        request.app.filestorage = Mock()

        layout = ElectionCompoundLayout(compound, request)
        assert layout.pdf_path == f'pdf/election-{ts}.de.pdf'
        assert layout.svg_path == f'svg/election-{ts}.None.any.svg'
        assert layout.svg_link == 'ElectionCompound/None-svg'
        assert layout.svg_name == 'electioncompound.svg'

        layout = ElectionCompoundLayout(compound, request, 'party-strengths')
        assert layout.pdf_path == f'pdf/election-{ts}.de.pdf'
        assert layout.svg_path == f'svg/election-{ts}.party-strengths.any.svg'
        assert layout.svg_link == 'ElectionCompound/party-strengths-svg'
        assert layout.svg_name == 'electioncompound-party-strengths.svg'

        layout = ElectionCompoundLayout(compound, request, 'parties-panachage')
        assert layout.pdf_path == f'pdf/election-{ts}.de.pdf'
        assert (
            layout.svg_path == f'svg/election-{ts}.parties-panachage.any.svg'
        )
        assert layout.svg_link == 'ElectionCompound/parties-panachage-svg'
        assert layout.svg_name == 'electioncompound-panachage.svg'


def test_election_compound_layout_menu_majorz(session):
    election = Election(
        title="Election",
        domain='region',
        date=date(2011, 1, 1)
    )
    compound = ElectionCompound(
        title="Elections",
        domain='canton',
        date=date(2011, 1, 1)
    )
    session.add(election)
    session.add(compound)
    session.flush()
    compound.elections = [election]

    request = DummyRequest()
    assert ElectionCompoundLayout(compound, request).menu == []
    assert ElectionCompoundLayout(compound, request, 'data').menu == []

    election.results.append(
        ElectionResult(
            name='1',
            entity_id=1,
            counted=True,
            eligible_voters=500,
        )
    )
    assert ElectionCompoundLayout(compound, request).menu == [
        ('__districts', 'ElectionCompound/districts', False, []),
        ('Elected candidates', 'ElectionCompound/candidates', False, []),
        ('Election statistics', 'ElectionCompound/statistics', False, []),
        ('Downloads', 'ElectionCompound/data', False, [])
    ]
    assert ElectionCompoundLayout(compound, request, 'data').menu == [
        ('__districts', 'ElectionCompound/districts', False, []),
        ('Elected candidates', 'ElectionCompound/candidates', False, []),
        ('Election statistics', 'ElectionCompound/statistics', False, []),
        ('Downloads', 'ElectionCompound/data', True, [])
    ]


def test_election_compound_layout_menu_proporz(session):
    election = ProporzElection(
        title="Election",
        domain='region',
        date=date(2011, 1, 1)
    )
    compound = ElectionCompound(
        title="Elections",
        domain='canton',
        date=date(2011, 1, 1)
    )
    session.add(election)
    session.add(compound)
    session.flush()
    compound.elections = [election]

    request = DummyRequest()
    assert ElectionCompoundLayout(compound, request).menu == []
    assert ElectionCompoundLayout(compound, request, 'data').menu == []

    election.results.append(
        ElectionResult(
            name='1',
            entity_id=1,
            counted=True,
            eligible_voters=500,
        )
    )
    assert ElectionCompoundLayout(compound, request).menu == [
        ('__districts', 'ElectionCompound/districts', False, []),
        ('Elected candidates', 'ElectionCompound/candidates', False, []),
        ('Election statistics', 'ElectionCompound/statistics', False, []),
        ('Downloads', 'ElectionCompound/data', False, [])
    ]
    assert ElectionCompoundLayout(compound, request, 'data').menu == [
        ('__districts', 'ElectionCompound/districts', False, []),
        ('Elected candidates', 'ElectionCompound/candidates', False, []),
        ('Election statistics', 'ElectionCompound/statistics', False, []),
        ('Downloads', 'ElectionCompound/data', True, [])
    ]

    compound.party_results.append(
        PartyResult(
            year=2017,
            number_of_mandates=0,
            votes=0,
            total_votes=100,
            name='A',
        )
    )
    compound.panachage_results.append(
        PanachageResult(target='t', source='t ', votes=0)
    )

    assert ElectionCompoundLayout(compound, request).menu == [
        ('__districts', 'ElectionCompound/districts', False, []),
        ('Elected candidates', 'ElectionCompound/candidates', False, []),
        ('Panachage', 'ElectionCompound/parties-panachage', False, []),
        ('Election statistics', 'ElectionCompound/statistics', False, []),
        ('Downloads', 'ElectionCompound/data', False, [])
    ]

    compound.show_party_strengths = True

    assert ElectionCompoundLayout(compound, request).menu == [
        ('__districts', 'ElectionCompound/districts', False, []),
        ('Elected candidates', 'ElectionCompound/candidates', False, []),
        ('Party strengths', 'ElectionCompound/party-strengths', False, []),
        ('Panachage', 'ElectionCompound/parties-panachage', False, []),
        ('Election statistics', 'ElectionCompound/statistics', False, []),
        ('Downloads', 'ElectionCompound/data', False, [])
    ]

    compound.show_party_strengths = False
    compound.show_mandate_allocation = True

    assert ElectionCompoundLayout(compound, request).menu == [
        ('__districts', 'ElectionCompound/districts', False, []),
        ('Elected candidates', 'ElectionCompound/candidates', False, []),
        (
            'Mandate allocation', 'ElectionCompound/mandate-allocation', False,
            []
        ),
        ('Panachage', 'ElectionCompound/parties-panachage', False, []),
        ('Election statistics', 'ElectionCompound/statistics', False, []),
        ('Downloads', 'ElectionCompound/data', False, [])
    ]


@pytest.mark.parametrize('tab,expected', [
    ('districts', 'ElectionCompound/districts-table'),
    ('candidates', 'ElectionCompound/candidates-table'),
    ('mandate-allocation', None),
    ('party-strengths', None),
    ('parties-panachage', None),
    ('data', None)

])
def test_election_compound_layout_table_links(tab, expected):
    # Test link depending on tab
    election = ElectionCompound(date=date(2100, 1, 1), domain='federation')
    layout = ElectionCompoundLayout(election, DummyRequest(), tab=tab)
    assert expected == layout.table_link
