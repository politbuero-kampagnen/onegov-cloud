from freezegun import freeze_time
from onegov.election_day.models import Canton
from onegov.election_day.models import Municipality
from onegov.election_day.models import Principal
from textwrap import dedent


SUPPORTED_YEARS = list(range(2002, 2021 + 1))

SUPPORTED_YEARS_MAP = list(range(2013, 2021 + 1))
SUPPORTED_YEARS_NO_MAP = list(set(SUPPORTED_YEARS) - set(SUPPORTED_YEARS_MAP))

SUPPORTED_YEARS_MAP_ADDITIONAL = list(range(2004, 2021 + 1))
SUPPORTED_YEARS_NO_MAP_ADDITIONAL = list(
    set(SUPPORTED_YEARS) - set(SUPPORTED_YEARS_MAP_ADDITIONAL)
)


def test_principal_load_canton():
    principal = Principal.from_yaml(dedent("""
        name: Kanton Zug
        canton: zg
    """))

    assert isinstance(principal, Canton)
    assert principal.name == 'Kanton Zug'
    assert principal.id == 'zg'
    assert principal.domain == 'canton'
    assert list(principal.domains_election.keys()) == [
        'federation', 'region', 'canton'
    ]
    assert list(principal.domains_vote.keys()) == ['federation', 'canton']
    assert len(principal.entities)
    assert len(list(principal.entities.values())[0])

    assert principal.logo is None
    assert principal.color == '#000'
    assert principal.base is None
    assert principal.base_domain is None
    assert principal.analytics is None
    assert principal.use_maps is True
    assert principal.has_districts is False
    assert principal.fetch == {}
    assert principal.webhooks == {}
    assert principal.sms_notification is None
    assert principal.email_notification is None
    assert principal.wabsti_import is False
    assert principal.pdf_signing == {}
    assert principal.open_data == {}
    assert principal.hidden_elements == {}
    assert principal.publish_intermediate_results == {
        'vote': False, 'election': False, 'election_compound': False
    }


def test_principal_load_municipality_with_static_data():
    principal = Principal.from_yaml(dedent("""
        name: Stadt Bern
        municipality: '351'
    """))
    assert isinstance(principal, Municipality)
    assert principal.name == 'Stadt Bern'
    assert principal.id == '351'
    assert principal.domain == 'municipality'
    assert list(principal.domains_election.keys()) == [
        'federation', 'canton', 'municipality'
    ]
    assert list(principal.domains_vote.keys()) == [
        'federation', 'canton', 'municipality'
    ]
    assert principal.has_quarters is True
    assert len(principal.entities)
    assert len(list(principal.entities.values())[0])

    assert principal.logo is None
    assert principal.color == '#000'
    assert principal.base is None
    assert principal.base_domain is None
    assert principal.analytics is None
    assert principal.use_maps is False
    assert principal.has_districts is False
    assert principal.fetch == {}
    assert principal.webhooks == {}
    assert principal.sms_notification is None
    assert principal.email_notification is None
    assert principal.wabsti_import is False
    assert principal.pdf_signing == {}


def test_principal_load_municipality_wo_static_data():
    principal = Principal.from_yaml(dedent("""
        name: Kriens
        municipality: '1059'
    """))
    assert isinstance(principal, Municipality)
    assert principal.name == 'Kriens'
    assert principal.id == '1059'
    assert principal.domain == 'municipality'
    assert list(principal.domains_election.keys()) == [
        'federation', 'canton', 'municipality'
    ]
    assert list(principal.domains_vote.keys()) == [
        'federation', 'canton', 'municipality'
    ]
    assert principal.has_quarters is False
    assert len(principal.entities)
    assert len(list(principal.entities.values())[0]) == 1

    assert principal.logo is None
    assert principal.color == '#000'
    assert principal.base is None
    assert principal.base_domain is None
    assert principal.analytics is None
    assert principal.use_maps is False
    assert principal.has_districts is False
    assert principal.fetch == {}
    assert principal.webhooks == {}
    assert principal.sms_notification is None
    assert principal.email_notification is None
    assert principal.wabsti_import is False
    assert principal.pdf_signing == {}


def test_principal_load_options():
    principal = Principal.from_yaml(dedent("""
        name: Kanton Zug
        canton: zg
        base: 'http://www.zg.ch'
        analytics: "<script type=\\"text/javascript\\"></script>"
        use_maps: false
        wabsti_import: true
        fetch:
            steinhausen:
                - municipality
            baar:
                - municipality
        webhooks:
            'http://abc.com/1':
            'http://abc.com/2':
                My-Header: My-Value
        sms_notification: 'https://wab.zg.ch'
        email_notification: true
        pdf_signing:
            url: 'http://abc.com/3'
            login: user
            password: pass
            reason: election and vote results
        open_data:
            id: kanton-zug
            name: Staatskanzlei Kanton Zug
            mail: info@zg.ch
        hidden_elements:
          always:
            candidate-by-entity:
              percentages: True
          intermediate_results:
            connections:
              chart: True
          tabs:
            elections:
              - lists
    """))
    assert isinstance(principal, Canton)
    assert principal.id == 'zg'
    assert principal.domain == 'canton'
    assert list(principal.domains_election.keys()) == [
        'federation', 'region', 'canton'
    ]
    assert list(principal.domains_vote.keys()) == ['federation', 'canton']

    assert principal.name == 'Kanton Zug'
    assert principal.logo is None
    assert principal.color == '#000'
    assert principal.base == 'http://www.zg.ch'
    assert principal.base_domain == 'zg.ch'
    assert principal.analytics == '<script type="text/javascript"></script>'
    assert principal.use_maps is True
    assert principal.has_districts is False
    assert principal.hidden_tabs == {'elections': ['lists']}
    assert principal.fetch == {
        'steinhausen': ['municipality'],
        'baar': ['municipality']
    }
    assert principal.webhooks == {
        'http://abc.com/1': None,
        'http://abc.com/2': {
            'My-Header': 'My-Value'
        }
    }
    assert principal.sms_notification == 'https://wab.zg.ch'
    assert principal.email_notification is True
    assert principal.wabsti_import is True
    assert principal.pdf_signing == {
        'url': 'http://abc.com/3',
        'login': 'user',
        'password': 'pass',
        'reason': 'election and vote results'
    }
    assert principal.open_data == {
        'id': 'kanton-zug',
        'name': 'Staatskanzlei Kanton Zug',
        'mail': 'info@zg.ch'
    }

    assert principal.hidden_elements == {
        'always': {
            'candidate-by-entity': {'percentages': True}
        },
        'intermediate_results': {
            'connections': {'chart': True}
        },
        'tabs': {'elections': ['lists']}
    }


def test_canton_entities():
    principal = Canton(name='Zug', canton='zg')
    entities = {
        1701: {'name': 'Baar'},
        1702: {'name': 'Cham'},
        1703: {'name': 'Hünenberg'},
        1704: {'name': 'Menzingen'},
        1705: {'name': 'Neuheim'},
        1706: {'name': 'Oberägeri'},
        1707: {'name': 'Risch'},
        1708: {'name': 'Steinhausen'},
        1709: {'name': 'Unterägeri'},
        1710: {'name': 'Walchwil'},
        1711: {'name': 'Zug'},
    }
    assert principal.entities == {
        year: entities for year in SUPPORTED_YEARS
    }

    # All cantons
    for canton in principal.CANTONS:
        principal = Canton(name=canton, canton=canton)
        for year in SUPPORTED_YEARS:
            assert principal.entities[year]


def test_canton_has_districts():
    assert Canton(name='gr', canton='gr').has_districts is True
    assert Canton(name='sg', canton='sg').has_districts is True
    assert Canton(name='sz', canton='sz').has_districts is True
    assert Canton(name='zg', canton='zg').has_districts is False


def test_municipality_entities():
    # Municipality without quarters
    with freeze_time("{}-01-01".format(SUPPORTED_YEARS[-1])):
        principal = Municipality(name='Kriens', municipality='1059')
        assert principal.entities == {
            year: {1059: {'name': 'Kriens'}} for year in SUPPORTED_YEARS
        }

    # Municipality with quarters
    principal = Municipality(name='Bern', municipality='351')
    entities = {
        1: {'name': 'Innere Stadt'},
        2: {'name': 'Länggasse/Felsenau'},
        3: {'name': 'Mattenhof/Weissenbühl'},
        4: {'name': 'Kirchenfeld/Schosshalde'},
        5: {'name': 'Breitenrain/Lorraine'},
        6: {'name': 'Bümpliz/Bethlehem'},
    }
    assert principal.entities == {year: entities for year in SUPPORTED_YEARS}


def test_principal_years_available():
    # Municipality without quarters/map
    with freeze_time("{}-01-01".format(SUPPORTED_YEARS[-1])):
        principal = Municipality(name='Kriens', municipality='1059')
        assert not principal.is_year_available(2000)
        assert not principal.is_year_available(2000, map_required=False)
        for year in SUPPORTED_YEARS:
            assert not principal.is_year_available(year)
            assert principal.is_year_available(year, map_required=False)

    # Municipality with quarters/map
    principal = Municipality(name='Bern', municipality='351')
    assert not principal.is_year_available(2000)
    assert not principal.is_year_available(2000, map_required=False)
    for year in SUPPORTED_YEARS_NO_MAP:
        assert not principal.is_year_available(year)
        assert principal.is_year_available(year, map_required=False)
    for year in SUPPORTED_YEARS_MAP:
        assert principal.is_year_available(year)
        assert principal.is_year_available(year, map_required=False)

    # Cantons
    for canton in Canton.CANTONS:
        principal = Canton(name=canton, canton=canton)

        if canton in {'bl', 'sg', 'zg'}:
            # Canton with additional map data
            for year in SUPPORTED_YEARS_NO_MAP_ADDITIONAL:
                assert not principal.is_year_available(year)
                assert principal.is_year_available(year, map_required=False)
            for year in SUPPORTED_YEARS_MAP_ADDITIONAL:
                assert principal.is_year_available(year)
                assert principal.is_year_available(year, map_required=False)
        else:
            # Canton with normal map data
            for year in SUPPORTED_YEARS_NO_MAP:
                assert not principal.is_year_available(year)
                assert principal.is_year_available(year, map_required=False)
            for year in SUPPORTED_YEARS_MAP:
                assert principal.is_year_available(year)
                assert principal.is_year_available(year, map_required=False)


def test_principal_notifications_enabled():
    assert Municipality(
        name='Kriens', municipality='1059'
    ).notifications is False

    assert Municipality(
        name='Kriens', municipality='1059',
        webhooks={'a', 'b'}
    ).notifications is True

    assert Municipality(
        name='Kriens', municipality='1059',
        sms_notification='https://wab.kriens.ch'
    ).notifications is True

    assert Municipality(
        name='Kriens', municipality='1059',
        email_notification=True
    ).notifications is True

    assert Municipality(
        name='Kriens', municipality='1059',
        webhooks={'a', 'b'},
        sms_notification='https://wab.kriens.ch',
        email_notification=True
    ).notifications is True


def test_principal_label(election_day_app):

    def translate(text, locale):
        translator = election_day_app.translations.get(locale)
        return text.interpolate(translator.gettext(text))

    # Default (Canton)
    principal = Canton(name='sg', canton='sg')
    for label, locale, result in (
        ('entity', 'de_CH', 'Gemeinde'),
        ('entity', 'fr_CH', 'Commune'),
        ('entity', 'it_CH', 'Comune'),
        ('entity', 'rm_CH', 'Vischnanca'),
        ('entities', 'de_CH', 'Gemeinden'),
        ('entities', 'fr_CH', 'Communes'),
        ('entities', 'it_CH', 'Comuni'),
        ('entities', 'rm_CH', 'Vischnancas'),
        ('district', 'de_CH', 'Wahlkreis'),
        ('district', 'fr_CH', 'Circonscription électorale'),
        ('district', 'it_CH', 'Distretto elettorale'),
        ('district', 'rm_CH', 'Circul electoral'),
        ('districts', 'de_CH', 'Wahlkreise'),
        ('districts', 'fr_CH', 'Circonscriptions électorales'),
        ('districts', 'it_CH', 'Distretti elettorali'),
        ('districts', 'rm_CH', 'Circuls electorals'),
    ):
        assert translate(principal.label(label), locale) == result

    # BL
    principal = Canton(name='bl', canton='bl')
    for label, locale, result in (
        ('entity', 'de_CH', 'Gemeinde'),
        ('entity', 'fr_CH', 'Commune'),
        ('entity', 'it_CH', 'Comune'),
        ('entity', 'rm_CH', 'Vischnanca'),
        ('entities', 'de_CH', 'Gemeinden'),
        ('entities', 'fr_CH', 'Communes'),
        ('entities', 'it_CH', 'Comuni'),
        ('entities', 'rm_CH', 'Vischnancas'),
        ('district', 'de_CH', 'Bezirk'),
        ('district', 'fr_CH', 'District électoral'),
        ('district', 'it_CH', 'Distretto elettorale'),
        ('district', 'rm_CH', 'Circul electoral'),
        ('districts', 'de_CH', 'Bezirke'),
        ('districts', 'fr_CH', 'Districts électorales'),
        ('districts', 'it_CH', 'Distretti elettorali'),
        ('districts', 'rm_CH', 'Circuls electorals'),
    ):
        assert translate(principal.label(label), locale) == result

    # GR
    principal = Canton(name='gr', canton='gr')
    for label, locale, result in (
        ('entity', 'de_CH', 'Gemeinde'),
        ('entity', 'fr_CH', 'Commune'),
        ('entity', 'it_CH', 'Comune'),
        ('entity', 'rm_CH', 'Vischnanca'),
        ('entities', 'de_CH', 'Gemeinden'),
        ('entities', 'fr_CH', 'Communes'),
        ('entities', 'it_CH', 'Comuni'),
        ('entities', 'rm_CH', 'Vischnancas'),
        ('district', 'de_CH', 'Region'),
        ('district', 'fr_CH', 'Région'),
        ('district', 'it_CH', 'Regione'),
        ('district', 'rm_CH', 'Regiun'),
        ('districts', 'de_CH', 'Regionen'),
        ('districts', 'fr_CH', 'Régions'),
        ('districts', 'it_CH', 'Regioni'),
        ('districts', 'rm_CH', 'Regiuns'),
    ):
        assert translate(principal.label(label), locale) == result

    # SZ
    principal = Canton(name='sz', canton='sz')
    for label, locale, result in (
        ('entity', 'de_CH', 'Gemeinde'),
        ('entity', 'fr_CH', 'Commune'),
        ('entity', 'it_CH', 'Comune'),
        ('entity', 'rm_CH', 'Vischnanca'),
        ('entities', 'de_CH', 'Gemeinden'),
        ('entities', 'fr_CH', 'Communes'),
        ('entities', 'it_CH', 'Comuni'),
        ('entities', 'rm_CH', 'Vischnancas'),
        ('district', 'de_CH', 'Bezirk'),
        ('district', 'fr_CH', 'District électoral'),
        ('district', 'it_CH', 'Distretto elettorale'),
        ('district', 'rm_CH', 'Circul electoral'),
        ('districts', 'de_CH', 'Bezirke'),
        ('districts', 'fr_CH', 'Districts électorales'),
        ('districts', 'it_CH', 'Distretti elettorali'),
        ('districts', 'rm_CH', 'Circuls electorals'),
    ):
        assert translate(principal.label(label), locale) == result

    # Bern
    principal = Municipality(name='Be', municipality='351')
    for label, locale, result in (
        ('entity', 'de_CH', 'Stadtteil'),
        ('entities', 'de_CH', 'Stadtteile')
    ):
        assert translate(principal.label(label), locale) == result
