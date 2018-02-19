import tarfile

from datetime import date
from io import BytesIO
from onegov.ballot import Election
from onegov.core.csv import convert_list_of_dicts_to_csv
from onegov.core.utils import module_path
from onegov.election_day.formats import import_election_internal_majorz
from onegov.election_day.models import Canton
from onegov.election_day.models import Municipality
from pytest import mark


@mark.parametrize("tar_file", [
    module_path('onegov.election_day',
                'tests/fixtures/internal_election.tar.gz'),
])
def test_import_internal_majorz(session, tar_file):
    session.add(
        Election(
            title='election',
            domain='canton',
            date=date(2015, 10, 18),
            number_of_mandates=2,
        )
    )
    session.flush()
    election = session.query(Election).one()

    principal = Canton(canton='zg')

    # The tar file contains results from ZG from the 18.10.2015 (v1.13.1)
    # and results from Bern from the 25.11.2015 (v1.13.1)
    with tarfile.open(tar_file, 'r|gz') as f:
        csv_majorz = f.extractfile(f.next()).read()
        f.extractfile(f.next()).read()
        csv_communal = f.extractfile(f.next()).read()

    # Test federal majorz
    errors = import_election_internal_majorz(
        election, principal, BytesIO(csv_majorz), 'text/plain',
    )

    assert not errors
    assert election.completed
    assert election.progress == (11, 11)
    assert election.results.count() == 11
    assert election.absolute_majority == 18191
    assert election.eligible_voters == 73355
    assert election.accounted_ballots == 38710
    assert election.accounted_votes == 72761
    assert election.blank_ballots == 63
    assert election.invalid_ballots == 115
    assert round(election.turnout, 2) == 53.01
    assert election.allocated_mandates == 2
    assert sorted(election.elected_candidates) == [
        ('Joachim', 'Eder'), ('Peter', 'Hegglin')
    ]

    # ... roundtrip
    csv = convert_list_of_dicts_to_csv(election.export()).encode('utf-8')

    errors = import_election_internal_majorz(
        election, principal, BytesIO(csv), 'text/plain'
    )

    assert not errors
    assert election.completed
    assert election.progress == (11, 11)
    assert election.results.count() == 11
    assert election.absolute_majority == 18191
    assert election.eligible_voters == 73355
    assert election.accounted_ballots == 38710
    assert election.accounted_votes == 72761
    assert election.blank_ballots == 63
    assert election.invalid_ballots == 115
    assert round(election.turnout, 2) == 53.01
    assert election.allocated_mandates == 2
    assert sorted(election.elected_candidates) == [
        ('Joachim', 'Eder'), ('Peter', 'Hegglin')
    ]

    # Test communal majorz without quarters
    election.type = 'majorz'
    election.number_of_mandates = 1
    principal = Municipality(municipality='1059')

    csv = (
        '\n'.join((
            ','.join((
                'election_absolute_majority',
                'election_status',
                'entity_id',
                'entity_counted',
                'entity_eligible_voters',
                'entity_received_ballots',
                'entity_blank_ballots',
                'entity_invalid_ballots',
                'entity_blank_votes',
                'entity_invalid_votes',
                'list_name',
                'list_id',
                'list_number_of_mandates',
                'list_votes',
                'list_connection',
                'list_connection_parent',
                'candidate_family_name',
                'candidate_first_name',
                'candidate_id',
                'candidate_elected',
                'candidate_votes',
                'candidate_party',
            )),
            (
                '3294,,1059,True,18699,6761,124,51,0,0,,,,,,,'
                'Koch,Patrick,1,False,,1621,'
            ),
            (
                '3294,,1059,True,18699,6761,124,51,0,0,,,,,,,'
                'Konrad,Simon,2,False,,1707,'
            ),
            (
                '3294,,1059,True,18699,6761,124,51,0,0,,,,,,,'
                'Faé,Franco,3,False,,3176,'
            ),
            (
                '3294,,1059,True,18699,6761,124,51,0,0,,,,,,,'
                'Vereinzelte,,4,False,,82,'
            ),
        ))
    ).encode('utf-8')

    errors = import_election_internal_majorz(
        election, principal, BytesIO(csv), 'text/plain',
    )

    assert not errors
    assert election.completed
    assert election.progress == (1, 1)
    assert election.results.count() == 1
    assert election.absolute_majority == 3294
    assert election.eligible_voters == 18699
    assert election.blank_ballots == 124
    assert election.invalid_ballots == 51
    assert round(election.turnout, 2) == 36.16
    assert election.allocated_mandates == 0
    assert election.candidates.count() == 4

    # ... roundtrip
    csv = convert_list_of_dicts_to_csv(election.export()).encode('utf-8')

    errors = import_election_internal_majorz(
        election, principal, BytesIO(csv), 'text/plain'
    )

    assert not errors
    assert election.completed
    assert election.progress == (1, 1)
    assert election.results.count() == 1
    assert election.absolute_majority == 3294
    assert election.eligible_voters == 18699
    assert election.blank_ballots == 124
    assert election.invalid_ballots == 51
    assert round(election.turnout, 2) == 36.16
    assert election.allocated_mandates == 0
    assert election.candidates.count() == 4

    # Test communal majorz with quarters
    election.type = 'majorz'
    election.number_of_mandates = 1
    principal = Municipality(municipality='351')

    errors = import_election_internal_majorz(
        election, principal, BytesIO(csv_communal), 'text/plain',
    )

    assert not errors
    assert election.completed
    assert election.progress == (6, 6)
    assert election.results.count() == 6
    assert election.absolute_majority == 12606
    assert election.eligible_voters == 82497
    assert election.blank_ballots == 1274
    assert election.invalid_ballots == 2797
    assert round(election.turnout, 2) == 35.49
    assert election.allocated_mandates == 1
    assert sorted(election.elected_candidates) == [('Tschäppät', 'Alexander')]

    # ... roundtrip
    csv = convert_list_of_dicts_to_csv(election.export()).encode('utf-8')

    errors = import_election_internal_majorz(
        election, principal, BytesIO(csv), 'text/plain'
    )

    assert not errors
    assert election.completed
    assert election.progress == (6, 6)
    assert election.results.count() == 6
    assert election.absolute_majority == 12606
    assert election.eligible_voters == 82497
    assert election.blank_ballots == 1274
    assert election.invalid_ballots == 2797
    assert round(election.turnout, 2) == 35.49
    assert election.allocated_mandates == 1
    assert sorted(election.elected_candidates) == [('Tschäppät', 'Alexander')]


def test_import_internal_majorz_missing_headers(session):
    session.add(
        Election(
            title='election',
            domain='canton',
            date=date(2015, 10, 18),
            number_of_mandates=6,
        )
    )
    session.flush()
    election = session.query(Election).one()
    principal = Canton(canton='sg')

    errors = import_election_internal_majorz(
        election, principal,
        BytesIO((
            '\n'.join((
                ','.join((
                    'election_absolute_majority',
                    'election_status',
                    'entity_id',
                    'entity_counted',
                    'entity_eligible_voters',
                    'entity_received_ballots',
                    'entity_blank_ballots',
                    'entity_invalid_ballots',
                    'entity_blank_votes',
                    'entity_invalid_votes',
                    'candidate_family_name',
                    'candidate_first_name',
                    'candidate_id',
                    'candidate_votes',
                    'candidate_party',
                )),
            ))
        ).encode('utf-8')), 'text/plain',
    )
    assert [(e.error.interpolate()) for e in errors] == [
        ("Missing columns: 'candidate_elected'")
    ]


def test_import_internal_majorz_invalid_values(session):
    session.add(
        Election(
            title='election',
            domain='canton',
            date=date(2015, 10, 18),
            number_of_mandates=6,
        )
    )
    session.flush()
    election = session.query(Election).one()
    principal = Canton(canton='sg')

    errors = import_election_internal_majorz(
        election, principal,
        BytesIO((
            '\n'.join((
                ','.join((
                    'election_absolute_majority',
                    'election_status',
                    'entity_id',
                    'entity_counted',
                    'entity_eligible_voters',
                    'entity_received_ballots',
                    'entity_blank_ballots',
                    'entity_invalid_ballots',
                    'entity_blank_votes',
                    'entity_invalid_votes',
                    'candidate_family_name',
                    'candidate_first_name',
                    'candidate_id',
                    'candidate_elected',
                    'candidate_votes',
                    'candidate_party',
                )),
                ','.join((
                    'xxx',  # election_absolute_majority
                    'xxx',  # election_status
                    'xxx',  # entity_id
                    'xxx',  # entity_counted
                    'xxx',  # entity_eligible_voters
                    'xxx',  # entity_received_ballots
                    'xxx',  # entity_blank_ballots
                    'xxx',  # entity_invalid_ballots
                    'xxx',  # entity_blank_votes
                    'xxx',  # entity_invalid_votes
                    'xxx',  # candidate_family_name
                    'xxx',  # candidate_first_name
                    'xxx',  # candidate_id
                    'xxx',  # candidate_elected
                    'xxx',  # candidate_votes
                    'xxx',  # candidate_party
                )),
                ','.join((
                    '',  # election_absolute_majority
                    'unknown',  # election_status
                    '1234',  # entity_id
                    'True',  # entity_counted
                    '100',  # entity_eligible_voters
                    '10',  # entity_received_ballots
                    '0',  # entity_blank_ballots
                    '0',  # entity_invalid_ballots
                    '0',  # entity_blank_votes
                    '0',  # entity_invalid_votes
                    '',  # candidate_family_name
                    '',  # candidate_first_name
                    '',  # candidate_id
                    '',  # candidate_elected
                    '',  # candidate_votes
                    '',  # candidate_party
                )),
            ))
        ).encode('utf-8')), 'text/plain',
    )

    assert sorted([(e.line, e.error.interpolate()) for e in errors]) == [
        (2, 'Invalid candidate results'),
        (2, 'Invalid candidate values'),
        (2, 'Invalid election values'),
        (2, 'Invalid entity values'),
        (2, 'Invalid status'),
        (3, '1234 is unknown'),
    ]


def test_import_internal_majorz_expats(session):
    session.add(
        Election(
            title='election',
            domain='canton',
            date=date(2015, 10, 18),
            number_of_mandates=6,
        )
    )
    session.flush()
    election = session.query(Election).one()
    principal = Canton(canton='zg')

    for entity_id in (9170, 0):
        errors = import_election_internal_majorz(
            election, principal,
            BytesIO((
                '\n'.join((
                    ','.join((
                        'election_absolute_majority',
                        'election_status',
                        'entity_id',
                        'entity_counted',
                        'entity_eligible_voters',
                        'entity_received_ballots',
                        'entity_blank_ballots',
                        'entity_invalid_ballots',
                        'entity_blank_votes',
                        'entity_invalid_votes',
                        'candidate_family_name',
                        'candidate_first_name',
                        'candidate_id',
                        'candidate_elected',
                        'candidate_votes',
                        'candidate_party',
                    )),
                    ','.join((
                        '',  # election_absolute_majority
                        'unknown',  # election_status
                        str(entity_id),  # entity_id
                        'True',  # entity_counted
                        '111',  # entity_eligible_voters
                        '11',  # entity_received_ballots
                        '1',  # entity_blank_ballots
                        '1',  # entity_invalid_ballots
                        '1',  # entity_blank_votes
                        '1',  # entity_invalid_votes
                        'xxx',  # candidate_family_name
                        'xxx',  # candidate_first_name
                        '1',  # candidate_id
                        'false',  # candidate_elected
                        '1',  # candidate_votes
                        '',  # candidate_party
                    ))
                ))
            ).encode('utf-8')), 'text/plain',
        )
        assert not errors
        assert election.results.filter_by(entity_id=0).one().invalid_votes == 1


def test_import_internal_majorz_temporary_results(session):
    session.add(
        Election(
            title='election',
            domain='canton',
            date=date(2015, 10, 18),
            number_of_mandates=6,
        )
    )
    session.flush()
    election = session.query(Election).one()
    principal = Canton(canton='zg')

    errors = import_election_internal_majorz(
        election, principal,
        BytesIO((
            '\n'.join((
                ','.join((
                    'election_absolute_majority',
                    'election_status',
                    'entity_id',
                    'entity_counted',
                    'entity_eligible_voters',
                    'entity_received_ballots',
                    'entity_blank_ballots',
                    'entity_invalid_ballots',
                    'entity_blank_votes',
                    'entity_invalid_votes',
                    'candidate_family_name',
                    'candidate_first_name',
                    'candidate_id',
                    'candidate_elected',
                    'candidate_votes',
                    'candidate_party',
                )),
                ','.join((
                    '',  # election_absolute_majority
                    'unknown',  # election_status
                    '1701',  # entity_id
                    'True',  # entity_counted
                    '111',  # entity_eligible_voters
                    '11',  # entity_received_ballots
                    '1',  # entity_blank_ballots
                    '1',  # entity_invalid_ballots
                    '1',  # entity_blank_votes
                    '1',  # entity_invalid_votes
                    'xxx',  # candidate_family_name
                    'xxx',  # candidate_first_name
                    '1',  # candidate_id
                    'false',  # candidate_elected
                    '1',  # candidate_votes
                    '',  # candidate_party
                )),
                ','.join((
                    '',  # election_absolute_majority
                    'unknown',  # election_status
                    '1702',  # entity_id
                    'False',  # entity_counted
                    '111',  # entity_eligible_voters
                    '11',  # entity_received_ballots
                    '1',  # entity_blank_ballots
                    '1',  # entity_invalid_ballots
                    '1',  # entity_blank_votes
                    '1',  # entity_invalid_votes
                    'xxx',  # candidate_family_name
                    'xxx',  # candidate_first_name
                    '1',  # candidate_id
                    'false',  # candidate_elected
                    '1',  # candidate_votes
                    '',  # candidate_party
                ))
            ))
        ).encode('utf-8')), 'text/plain',
    )
    assert not errors

    # 1 Counted, 1 Uncounted, 10 Missing
    assert election.progress == (1, 11)
