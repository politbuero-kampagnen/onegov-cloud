from datetime import date
from freezegun import freeze_time
from onegov.ballot import Candidate
from onegov.ballot import CandidateResult
from onegov.ballot import Election
from onegov.ballot import ElectionCompound
from onegov.ballot import ElectionResult
from onegov.ballot import List
from onegov.ballot import ListConnection
from onegov.ballot import ListResult
from onegov.ballot import PanachageResult
from onegov.ballot import PartyResult
from onegov.ballot import ProporzElection
from onegov.ballot.models.election.election_compound import \
    ElectionCompoundAssociation
from uuid import uuid4


def majorz_election():
    # election
    election = Election(
        title='Majorz',
        id='majorz',
        shortcode='2',
        domain='federation',
        date=date(2015, 6, 14),
        number_of_mandates=1,
        absolute_majority=144
    )
    election.title_translations['it_CH'] = 'Elezione'

    # candidates
    candidate_id_1 = uuid4()
    candidate_id_2 = uuid4()
    election.candidates.append(
        Candidate(
            id=candidate_id_1,
            elected=True,
            candidate_id='1',
            family_name='Quimby',
            first_name='Joe',
            party='Republican Party',
        )
    )
    election.candidates.append(
        Candidate(
            id=candidate_id_2,
            elected=False,
            candidate_id='2',
            family_name='Nahasapeemapetilon',
            first_name='Apu',
            party='Democratic Party',
        )
    )

    # results
    election_result = ElectionResult(
        name='name',
        entity_id=1,
        counted=True,
        eligible_voters=1000,
        received_ballots=500,
        blank_ballots=10,
        invalid_ballots=5,
        blank_votes=80,
        invalid_votes=120
    )
    election_result.candidate_results.append(
        CandidateResult(candidate_id=candidate_id_1, votes=520)
    )
    election_result.candidate_results.append(
        CandidateResult(candidate_id=candidate_id_2, votes=111)
    )
    election.results.append(election_result)
    return election


def proporz_election(
        title='Proporz',
        id='proporz',
        shortcode='1',
        domain='federation',
        date=date(2015, 6, 14),
        number_of_mandates=1,
        absolute_majority=144,
        status=None,
        after_pukelsheim=False
):

    # election
    election = ProporzElection(
        title=title,
        id=id,
        shortcode=shortcode,
        domain=domain,
        date=date,
        number_of_mandates=number_of_mandates,
        absolute_majority=absolute_majority,
        status=status,
        after_pukelsheim=after_pukelsheim
    )
    election.title_translations['it_CH'] = 'Elezione'

    # lists
    list_id_1 = uuid4()
    list_id_2 = uuid4()
    connection = ListConnection(connection_id='A')
    subconnection = ListConnection(id=uuid4(), connection_id='A.1')
    connection.children.append(subconnection)
    election.list_connections.append(connection)
    list_1 = List(
        id=list_id_1,
        list_id='1',
        number_of_mandates=1,
        name='Quimby Again!',
    )
    list_2 = List(
        id=list_id_2,
        list_id='2',
        number_of_mandates=0,
        name='Kwik-E-Major',
        connection_id=subconnection.id
    )
    election.lists.append(list_1)
    election.lists.append(list_2)

    # candidates
    candidate_id_1 = uuid4()
    candidate_id_2 = uuid4()
    election.candidates.append(
        Candidate(
            id=candidate_id_1,
            elected=True,
            candidate_id='1',
            list_id=list_id_1,
            family_name='Quimby',
            first_name='Joe',
            party='Republican Party',
        )
    )
    election.candidates.append(
        Candidate(
            id=candidate_id_2,
            elected=False,
            candidate_id='2',
            list_id=list_id_2,
            family_name='Nahasapeemapetilon',
            first_name='Apu',
            party='Democratic Party',
        )
    )

    # results
    election_result = ElectionResult(
        name='name',
        entity_id=1,
        counted=True,
        eligible_voters=1000,
        received_ballots=500,
        blank_ballots=10,
        invalid_ballots=5,
        blank_votes=80,
        invalid_votes=120
    )

    election_result.candidate_results.append(
        CandidateResult(candidate_id=candidate_id_1, votes=520)
    )
    election_result.candidate_results.append(
        CandidateResult(candidate_id=candidate_id_2, votes=111)
    )

    election_result.list_results.append(
        ListResult(list_id=list_id_1, votes=520)
    )
    election_result.list_results.append(
        ListResult(list_id=list_id_2, votes=111)
    )
    election.results.append(election_result)

    list_1.panachage_results.append(
        PanachageResult(source=list_2.list_id, votes=12)
    )
    list_1.panachage_results.append(
        PanachageResult(source='99', votes=4)
    )

    return election


def test_election_compound(session):
    session.add(
        ElectionCompound(
            title='Legislative Elections',
            domain='canton',
            date=date(2015, 6, 14),
        )
    )
    session.flush()
    election_compound = session.query(ElectionCompound).one()

    assert election_compound.elections == []
    assert election_compound.number_of_mandates == 0
    assert election_compound.allocated_mandates() == 0
    assert election_compound.counted is True
    assert election_compound.progress == (0, 0)
    assert election_compound.counted_entities == []
    assert election_compound.has_results == False
    assert election_compound.completed == True
    assert election_compound.elected_candidates == []
    assert election_compound.related_link is None

    # Add two elections
    session.add(
        Election(
            title="First election",
            domain='region',
            date=date(2015, 6, 14),
            number_of_mandates=1,
        )
    )
    session.add(
        Election(
            title="Second election",
            domain='region',
            date=date(2015, 6, 14),
            number_of_mandates=2,
        )
    )
    session.flush()

    election_compound.elections = session.query(Election).all()
    session.flush()
    assert set([election.id for election in election_compound.elections]) == {
        'first-election', 'second-election'
    }

    assert election_compound.number_of_mandates == 3
    assert election_compound.counted is False
    assert election_compound.progress == (0, 2)
    assert election_compound.counted_entities == []
    assert election_compound.allocated_mandates() == 0
    assert election_compound.has_results == False
    assert election_compound.completed == False
    assert election_compound.elected_candidates == []

    # Add results and candidates
    candidates = (('Paul', 'Peter'), ('Max', 'Miro'))
    for index, election in enumerate(election_compound.elections):
        election.results.append(
            ElectionResult(
                name='one',
                entity_id=1,
                counted=False,
                eligible_voters=200,
                received_ballots=150,
                blank_ballots=6,
                invalid_ballots=15,
                blank_votes=12,
                invalid_votes=9
            )
        )
        election.results.append(
            ElectionResult(
                name='two',
                entity_id=2,
                counted=False,
                eligible_voters=200,
                received_ballots=150,
                blank_ballots=6,
                invalid_ballots=15,
                blank_votes=12,
                invalid_votes=9
            )
        )
        election.candidates.append(
            Candidate(
                elected=False,
                candidate_id=str(index),
                family_name=candidates[index][0],
                first_name=candidates[index][1],
            )
        )

    assert election_compound.counted is False
    assert election_compound.progress == (0, 2)
    assert election_compound.counted_entities == []
    assert election_compound.allocated_mandates() == 0
    assert election_compound.has_results == False
    assert election_compound.completed == False

    # Set results as counted
    session.query(ElectionResult).first().counted = True
    assert election_compound.counted is False
    assert election_compound.progress == (0, 2)
    assert election_compound.counted_entities == []
    assert election_compound.allocated_mandates() == 0
    assert election_compound.has_results == True
    assert election_compound.completed == False

    for result in session.query(ElectionResult):
        result.counted = True
    assert election_compound.counted is True
    assert election_compound.progress == (2, 2)
    assert election_compound.counted_entities == [
        'First election', 'Second election'
    ]
    assert election_compound.allocated_mandates() == 0
    assert election_compound.completed == True

    # Set candidates as elected
    session.query(Candidate).filter_by(candidate_id='1').one().elected = True
    assert election_compound.elected_candidates == [('Miro', 'Max')]

    for candidate in session.query(Candidate):
        candidate.elected = True
    assert set(election_compound.elected_candidates) == {
        ('Miro', 'Max'), ('Peter', 'Paul')
    }

    # Add party results
    party_result = PartyResult(
        owner=election_compound.id,
        number_of_mandates=0,
        votes=0,
        total_votes=100,
        name='Libertarian',
        color='black'
    )
    session.add(party_result)
    session.flush()
    assert election_compound.party_results.one() == party_result

    # Add panachage results
    panachage_result = PanachageResult(
        owner=election_compound.id,
        source='A',
        target='B',
        votes=0,
    )
    session.add(panachage_result)
    session.flush()
    assert election_compound.panachage_results.one() == panachage_result

    # Clear results
    election_compound.clear_results()
    assert election_compound.party_results.first() == None
    assert election_compound.panachage_results.first() == None


def test_election_compound_id_generation(session):
    election_compound = ElectionCompound(
        title='Legislative Elections',
        domain='canton',
        date=date(2015, 6, 14),
    )
    session.add(election_compound)
    session.flush()

    assert election_compound.id == 'legislative-elections'

    election = ElectionCompound(
        title='Legislative Elections',
        domain='federation',
        date=date(2015, 6, 14),
    )

    session.add(election)
    session.flush()

    assert election.id == 'legislative-elections-1'


def test_election_compound_changes(session):
    with freeze_time("2014-01-01"):
        session.add(
            ElectionCompound(
                title='Elections',
                domain='canton',
                date=date(2015, 6, 14),
            )
        )
        session.flush()

    election_compound = session.query(ElectionCompound).one()
    assert election_compound.last_modified.isoformat().startswith('2014')
    assert election_compound.last_result_change is None

    with freeze_time("2015-01-01"):
        session.add(majorz_election())
        session.flush()
    with freeze_time("2016-01-01"):
        session.add(proporz_election())
        session.flush()
    assert election_compound.last_modified.isoformat().startswith('2014')
    assert election_compound.last_result_change is None

    with freeze_time("2011-01-01"):
        election_compound.elections = session.query(Election).all()
        session.flush()
    assert election_compound.last_modified.isoformat().startswith('2016')
    assert election_compound.last_result_change.isoformat().startswith('2016')

    with freeze_time("2017-01-01"):
        election_compound.title = 'elections'
        session.flush()
    assert election_compound.last_modified.isoformat().startswith('2017')
    assert election_compound.last_result_change.isoformat().startswith('2016')

    with freeze_time("2018-01-01"):
        election_compound.party_results.append(
            PartyResult(
                number_of_mandates=0,
                votes=0,
                total_votes=100,
                name='Libertarian',
                color='black'
            )
        )
        session.flush()
    assert election_compound.last_modified.isoformat().startswith('2018')
    assert election_compound.last_result_change.isoformat().startswith('2018')

    with freeze_time("2019-01-01"):
        election_compound.panachage_results.append(
            PanachageResult(
                source='A',
                target='B',
                votes=0
            )
        )
        session.flush()
    assert election_compound.last_modified.isoformat().startswith('2019')
    assert election_compound.last_result_change.isoformat().startswith('2019')

    with freeze_time("2020-01-01"):
        election_compound.elections[0].shortcode = '8'
        session.flush()
    assert election_compound.last_modified.isoformat().startswith('2020')
    assert election_compound.last_result_change.isoformat().startswith('2019')


def test_election_compound_export(session):
    session.add(
        ElectionCompound(
            title='Elections',
            domain='canton',
            date=date(2015, 6, 14),
        )
    )
    session.add(majorz_election())
    session.add(proporz_election())
    session.flush()
    election_compound = session.query(ElectionCompound).one()
    election_compound.title_translations['it_CH'] = 'Elezioni'

    assert election_compound.export() == []

    election_compound.elections = session.query(Election).filter_by(
        id='majorz'
    ).all()
    session.flush()
    exports = election_compound.export()
    assert exports[0] == {
        'compound_title_de_CH': 'Elections',
        'compound_title_fr_CH': '',
        'compound_title_it_CH': 'Elezioni',
        'compound_title_rm_CH': '',
        'compound_date': '2015-06-14',
        'compound_mandates': 1,
        'election_title_de_CH': 'Majorz',
        'election_title_fr_CH': '',
        'election_title_it_CH': 'Elezione',
        'election_title_rm_CH': '',
        'election_date': '2015-06-14',
        'election_domain': 'federation',
        'election_type': 'majorz',
        'election_mandates': 1,
        'election_absolute_majority': 144,
        'election_status': 'unknown',
        'entity_district': '',
        'entity_name': 'name',
        'entity_id': 1,
        'entity_counted': True,
        'entity_eligible_voters': 1000,
        'entity_received_ballots': 500,
        'entity_blank_ballots': 10,
        'entity_invalid_ballots': 5,
        'entity_unaccounted_ballots': 15,
        'entity_accounted_ballots': 485,
        'entity_blank_votes': 80,
        'entity_invalid_votes': 120,
        'entity_accounted_votes': 285,
        'candidate_family_name': 'Nahasapeemapetilon',
        'candidate_first_name': 'Apu',
        'candidate_id': '2',
        'candidate_elected': False,
        'candidate_party': 'Democratic Party',
        'candidate_votes': 111
    }
    assert exports[1] == {
        'compound_title_de_CH': 'Elections',
        'compound_title_fr_CH': '',
        'compound_title_it_CH': 'Elezioni',
        'compound_title_rm_CH': '',
        'compound_date': '2015-06-14',
        'compound_mandates': 1,
        'election_title_de_CH': 'Majorz',
        'election_title_fr_CH': '',
        'election_title_it_CH': 'Elezione',
        'election_title_rm_CH': '',
        'election_date': '2015-06-14',
        'election_domain': 'federation',
        'election_type': 'majorz',
        'election_mandates': 1,
        'election_absolute_majority': 144,
        'election_status': 'unknown',
        'entity_district': '',
        'entity_name': 'name',
        'entity_id': 1,
        'entity_counted': True,
        'entity_eligible_voters': 1000,
        'entity_received_ballots': 500,
        'entity_blank_ballots': 10,
        'entity_invalid_ballots': 5,
        'entity_unaccounted_ballots': 15,
        'entity_accounted_ballots': 485,
        'entity_blank_votes': 80,
        'entity_invalid_votes': 120,
        'entity_accounted_votes': 285,
        'candidate_family_name': 'Quimby',
        'candidate_first_name': 'Joe',
        'candidate_id': '1',
        'candidate_elected': True,
        'candidate_party': 'Republican Party',
        'candidate_votes': 520
    }

    election_compound.elections = session.query(Election).all()
    session.flush()
    exports = election_compound.export()

    assert exports[0] == {
        'compound_title_de_CH': 'Elections',
        'compound_title_fr_CH': '',
        'compound_title_it_CH': 'Elezioni',
        'compound_title_rm_CH': '',
        'compound_date': '2015-06-14',
        'compound_mandates': 2,
        'election_title_de_CH': 'Proporz',
        'election_title_fr_CH': '',
        'election_title_it_CH': 'Elezione',
        'election_title_rm_CH': '',
        'election_date': '2015-06-14',
        'election_domain': 'federation',
        'election_type': 'proporz',
        'election_mandates': 1,
        'election_absolute_majority': 144,
        'election_status': 'unknown',
        'entity_district': '',
        'entity_name': 'name',
        'entity_id': 1,
        'entity_counted': True,
        'entity_eligible_voters': 1000,
        'entity_received_ballots': 500,
        'entity_blank_ballots': 10,
        'entity_invalid_ballots': 5,
        'entity_unaccounted_ballots': 15,
        'entity_accounted_ballots': 485,
        'entity_blank_votes': 80,
        'entity_invalid_votes': 120,
        'entity_accounted_votes': 285,
        'list_name': 'Kwik-E-Major',
        'list_id': '2',
        'list_number_of_mandates': 0,
        'list_votes': 111,
        'list_connection': 'A.1',
        'list_connection_parent': 'A',
        'candidate_family_name': 'Nahasapeemapetilon',
        'candidate_first_name': 'Apu',
        'candidate_id': '2',
        'candidate_elected': False,
        'candidate_party': 'Democratic Party',
        'candidate_votes': 111,
        'panachage_votes_from_list_1': None,
        'panachage_votes_from_list_2': None,
        'panachage_votes_from_list_99': None
    }

    assert exports[1] == {
        'compound_title_de_CH': 'Elections',
        'compound_title_fr_CH': '',
        'compound_title_it_CH': 'Elezioni',
        'compound_title_rm_CH': '',
        'compound_date': '2015-06-14',
        'compound_mandates': 2,
        'election_title_de_CH': 'Proporz',
        'election_title_fr_CH': '',
        'election_title_it_CH': 'Elezione',
        'election_title_rm_CH': '',
        'election_date': '2015-06-14',
        'election_domain': 'federation',
        'election_type': 'proporz',
        'election_mandates': 1,
        'election_absolute_majority': 144,
        'election_status': 'unknown',
        'entity_district': '',
        'entity_name': 'name',
        'entity_id': 1,
        'entity_counted': True,
        'entity_eligible_voters': 1000,
        'entity_received_ballots': 500,
        'entity_blank_ballots': 10,
        'entity_invalid_ballots': 5,
        'entity_unaccounted_ballots': 15,
        'entity_accounted_ballots': 485,
        'entity_blank_votes': 80,
        'entity_invalid_votes': 120,
        'entity_accounted_votes': 285,
        'list_name': 'Quimby Again!',
        'list_id': '1',
        'list_number_of_mandates': 1,
        'list_votes': 520,
        'list_connection': None,
        'list_connection_parent': None,
        'candidate_family_name': 'Quimby',
        'candidate_first_name': 'Joe',
        'candidate_id': '1',
        'candidate_elected': True,
        'candidate_party': 'Republican Party',
        'candidate_votes': 520,
        'panachage_votes_from_list_1': None,
        'panachage_votes_from_list_2': 12,
        'panachage_votes_from_list_99': 4
    }

    assert exports[2] == {
        'compound_title_de_CH': 'Elections',
        'compound_title_fr_CH': '',
        'compound_title_it_CH': 'Elezioni',
        'compound_title_rm_CH': '',
        'compound_date': '2015-06-14',
        'compound_mandates': 2,
        'election_title_de_CH': 'Majorz',
        'election_title_fr_CH': '',
        'election_title_it_CH': 'Elezione',
        'election_title_rm_CH': '',
        'election_date': '2015-06-14',
        'election_domain': 'federation',
        'election_type': 'majorz',
        'election_mandates': 1,
        'election_absolute_majority': 144,
        'election_status': 'unknown',
        'entity_district': '',
        'entity_name': 'name',
        'entity_id': 1,
        'entity_counted': True,
        'entity_eligible_voters': 1000,
        'entity_received_ballots': 500,
        'entity_blank_ballots': 10,
        'entity_invalid_ballots': 5,
        'entity_unaccounted_ballots': 15,
        'entity_accounted_ballots': 485,
        'entity_blank_votes': 80,
        'entity_invalid_votes': 120,
        'entity_accounted_votes': 285,
        'candidate_family_name': 'Nahasapeemapetilon',
        'candidate_first_name': 'Apu',
        'candidate_id': '2',
        'candidate_elected': False,
        'candidate_party': 'Democratic Party',
        'candidate_votes': 111
    }

    assert exports[3] == {
        'compound_title_de_CH': 'Elections',
        'compound_title_fr_CH': '',
        'compound_title_it_CH': 'Elezioni',
        'compound_title_rm_CH': '',
        'compound_date': '2015-06-14',
        'compound_mandates': 2,
        'election_title_de_CH': 'Majorz',
        'election_title_fr_CH': '',
        'election_title_it_CH': 'Elezione',
        'election_title_rm_CH': '',
        'election_date': '2015-06-14',
        'election_domain': 'federation',
        'election_type': 'majorz',
        'election_mandates': 1,
        'election_absolute_majority': 144,
        'election_status': 'unknown',
        'entity_district': '',
        'entity_name': 'name',
        'entity_id': 1,
        'entity_counted': True,
        'entity_eligible_voters': 1000,
        'entity_received_ballots': 500,
        'entity_blank_ballots': 10,
        'entity_invalid_ballots': 5,
        'entity_unaccounted_ballots': 15,
        'entity_accounted_ballots': 485,
        'entity_blank_votes': 80,
        'entity_invalid_votes': 120,
        'entity_accounted_votes': 285,
        'candidate_family_name': 'Quimby',
        'candidate_first_name': 'Joe',
        'candidate_id': '1',
        'candidate_elected': True,
        'candidate_party': 'Republican Party',
        'candidate_votes': 520
    }


def test_election_compound_export_parties(session):
    session.add(
        ElectionCompound(
            title='Elections',
            domain='canton',
            date=date(2016, 6, 14),
        )
    )
    session.flush()
    election_compound = session.query(ElectionCompound).one()

    assert election_compound.export_parties() == []

    # Add party results
    election_compound.party_results.append(
        PartyResult(
            number_of_mandates=0,
            votes=0,
            total_votes=100,
            name='Libertarian',
            color='black',
            year=2012
        )
    )
    election_compound.party_results.append(
        PartyResult(
            number_of_mandates=2,
            votes=2,
            total_votes=50,
            name='Libertarian',
            color='black',
            year=2016
        )
    )
    election_compound.party_results.append(
        PartyResult(
            number_of_mandates=1,
            votes=1,
            total_votes=100,
            name='Conservative',
            color='red',
            year=2012
        )
    )
    election_compound.party_results.append(
        PartyResult(
            number_of_mandates=3,
            votes=3,
            total_votes=50,
            name='Conservative',
            color='red',
            year=2016
        )
    )

    assert election_compound.export_parties() == [
        {
            'year': 2016,
            'name': 'Conservative',
            'id': 0,
            'color': 'red',
            'mandates': 3,
            'total_votes': 50,
            'votes': 3,
        }, {
            'year': 2016,
            'name': 'Libertarian',
            'id': 1,
            'color': 'black',
            'mandates': 2,
            'total_votes': 50,
            'votes': 2,
        }, {
            'year': 2012,
            'name': 'Conservative',
            'id': 0,
            'color': 'red',
            'mandates': 1,
            'total_votes': 100,
            'votes': 1,
        }, {
            'year': 2012,
            'name': 'Libertarian',
            'id': 1,
            'color': 'black',
            'mandates': 0,
            'total_votes': 100,
            'votes': 0,
        }
    ]

    # Add panachage results
    for idx, source in enumerate(('Conservative', 'Libertarian', 'Other', '')):
        election_compound.panachage_results.append(
            PanachageResult(
                target='Conservative',
                source=source,
                votes=idx + 1
            )
        )
    election_compound.panachage_results.append(
        PanachageResult(
            target='Libertarian',
            source='Conservative',
            votes=5,
        )
    )
    assert election_compound.export_parties() == [
        {
            'year': 2016,
            'name': 'Conservative',
            'id': 0,
            'color': 'red',
            'mandates': 3,
            'total_votes': 50,
            'votes': 3,
            'panachage_votes_from_0': 1,
            'panachage_votes_from_1': 2,
            'panachage_votes_from_2': 3,
            'panachage_votes_from_999': 4,
        }, {
            'year': 2016,
            'name': 'Libertarian',
            'id': 1,
            'color': 'black',
            'mandates': 2,
            'total_votes': 50,
            'votes': 2,
            'panachage_votes_from_0': 5,
            'panachage_votes_from_1': '',
            'panachage_votes_from_2': '',
            'panachage_votes_from_999': '',
        }, {
            'color': '',
            'mandates': '',
            'name': 'Other',
            'id': 2,
            'total_votes': '',
            'votes': '',
            'year': 2016,
            'panachage_votes_from_0': '',
            'panachage_votes_from_1': '',
            'panachage_votes_from_2': '',
            'panachage_votes_from_999': '',
        }, {
            'year': 2012,
            'name': 'Conservative',
            'id': 0,
            'color': 'red',
            'mandates': 1,
            'total_votes': 100,
            'votes': 1,
            'panachage_votes_from_0': '',
            'panachage_votes_from_1': '',
            'panachage_votes_from_2': '',
            'panachage_votes_from_999': '',
        }, {
            'year': 2012,
            'name': 'Libertarian',
            'id': 1,
            'color': 'black',
            'mandates': 0,
            'total_votes': 100,
            'votes': 0,
            'panachage_votes_from_0': '',
            'panachage_votes_from_1': '',
            'panachage_votes_from_2': '',
            'panachage_votes_from_999': '',
        }, {
            'color': '',
            'mandates': '',
            'name': 'Other',
            'id': 2,
            'total_votes': '',
            'votes': '',
            'year': 2012,
            'panachage_votes_from_0': '',
            'panachage_votes_from_1': '',
            'panachage_votes_from_2': '',
            'panachage_votes_from_999': '',
        }
    ]


def test_election_compound_rename(session):
    session.add(majorz_election())
    session.add(proporz_election())
    session.flush()

    election_compound = ElectionCompound(
        title='Elections',
        id='elerctions',
        domain='canton',
        date=date(2015, 6, 14),
    )
    election_compound.elections = session.query(Election).all()
    session.add(election_compound)
    session.flush()

    query = session.query(
        ElectionCompoundAssociation.election_compound_id.distinct()
    )
    assert query.one()[0] == 'elerctions'

    election_compound.id = 'elections'
    assert query.one()[0] == 'elections'
    assert len(election_compound.elections) == 2

    session.flush()
    assert query.one()[0] == 'elections'
    assert len(election_compound.elections) == 2


def test_election_compound_doppelter_pukelsheim(session):

    election_compound = ElectionCompound(
        title='Elections',
        id='elerctions',
        domain='canton',
        date=date(2020, 3, 22),
    )

    proporz_1 = proporz_election(
        title='Proporz 1',
        id='1',
        shortcode='P1',
        domain='region',
        date=date(2020, 3, 22),
        number_of_mandates=1,
        status='interim'
    )

    proporz_2 = proporz_election(
        title='Proporz 2',
        id='2',
        shortcode='P2',
        domain='region',
        date=date(2020, 3, 22),
        number_of_mandates=1,
        status='final'
    )

    session.add_all((proporz_1, proporz_2))
    session.flush()

    # normal situation
    assert proporz_1.completed is False
    assert proporz_2.completed is True

    # test when no associations are set for the election or
    # compound election and election dates mismatch (fallback)
    proporz_2.after_pukelsheim = True
    assert proporz_2.completed is True

    # Create compound
    election_compound.elections = (proporz_1, proporz_2)
    session.add(election_compound)
    session.flush()
    assert proporz_2.compound == election_compound

    # Iterates over all election.competed that query compound itself
    # test to prevent maximum recursion depth
    assert election_compound.completed is False
    # Since his compound is not flagged to use Pukelsheim, use default
    assert proporz_2.completed is True

    proporz_1.status = 'final'
    assert proporz_1.completed is True

    proporz_1.after_pukelsheim = True
    assert proporz_1.completed is True

    election_compound.after_pukelsheim = True
    assert proporz_1.completed is False
    assert proporz_2.completed is False

    election_compound.pukelsheim_completed = True
    assert proporz_1.completed is True
    assert proporz_2.completed is True


def test_list_results(session):
    election_compound = ElectionCompound(
        title='Elections',
        domain='canton',
        date=date(2015, 6, 14),
    )
    session.add(election_compound)
    session.flush()

    assert election_compound.get_list_results().all() == []
    elections = [
        proporz_election(id='1'),
        proporz_election(id='2'),
        proporz_election(id='3')
    ]
    for election in elections:
        session.add(election)
    election_compound.elections = elections
    session.flush()

    assert election_compound.get_list_results().all() == [
        ('Quimby Again!', 3, 3 * 520),
        ('Kwik-E-Major', 0, 3 * 111)
    ]

    # Add another list
    list_id = uuid4()
    list_ = List(
        id=list_id,
        list_id='3',
        number_of_mandates=5,
        name='Burns burns!',
    )
    list_result = ListResult(
        list_id=list_id,
        votes=200
    )
    election_result = ElectionResult(
        name='name',
        entity_id=1,
        counted=True,
    )
    election_result.list_results.append(list_result)
    elections[0].lists.append(list_)
    elections[0].results.append(election_result)
    session.flush()

    assert election_compound.get_list_results().all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
        ('Burns burns!', 5, 200)
    ]

    # Test optional parameters
    # ... limit
    assert election_compound.get_list_results(limit=0).all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
        ('Burns burns!', 5, 200)
    ]
    assert election_compound.get_list_results(limit=None).all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
        ('Burns burns!', 5, 200)
    ]
    assert election_compound.get_list_results(limit=-5).all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
        ('Burns burns!', 5, 200)
    ]
    assert election_compound.get_list_results(limit=2).all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
    ]

    # ... names
    assert election_compound.get_list_results(names=[]).all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
        ('Burns burns!', 5, 200)
    ]
    assert election_compound.get_list_results(names=None).all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
        ('Burns burns!', 5, 200)
    ]
    assert election_compound.get_list_results(
        names=['Quimby Again!', 'Kwik-E-Major', 'All others']
    ).all() == [
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333),
    ]

    # ... order_by
    assert election_compound.get_list_results(
        order_by='number_of_mandates'
    ).all() == [
        ('Burns burns!', 5, 200),
        ('Quimby Again!', 3, 1560),
        ('Kwik-E-Major', 0, 333)
    ]

    # ... limit & names & order_by
    assert election_compound.get_list_results(
        limit=1,
        names=['Quimby Again!'],
        order_by='number_of_mandates'
    ).all() == [
        ('Quimby Again!', 3, 1560),
    ]
