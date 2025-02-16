from onegov.agency.collections import ExtendedAgencyCollection
from onegov.agency.collections import ExtendedPersonCollection
from onegov.agency.layout import AgencyCollectionLayout
from onegov.agency.layout import AgencyLayout
from onegov.agency.layout import ExtendedPersonCollectionLayout
from onegov.agency.layout import ExtendedPersonLayout
from onegov.agency.layout import MembershipLayout
from onegov.agency.models import ExtendedAgency
from onegov.agency.models import ExtendedPerson
from onegov.people import AgencyMembership


class DummyOrg(object):
    geo_provider = None
    open_files_target_blank = True


class DummyApp(object):
    org = DummyOrg()


class DummyRequest(object):
    locale = 'en'
    is_logged_in = False
    is_manager = False
    is_admin = False
    session = None
    permissions = {}

    def __init__(self):
        self.app = DummyApp()

    def translate(self, text):
        return str(text)

    def include(self, *args, **kwargs):
        pass

    def link(self, model, name=''):
        if isinstance(model, str):
            return f'{model}/{name}'
        return f'{model.__class__.__name__}/{name}'

    def exclude_invisible(self, objects):
        return objects

    def new_csrf_token(self):
        return 'x'

    def has_permission(self, model, permission):
        permissions = self.permissions.get(model.__class__.__name__, [])
        return permission.__name__ in permissions


def path(links):
    return '/'.join([link.attrs['href'].strip('/') for link in links])


def hrefs(items):
    for item in items:
        if hasattr(item, 'links'):
            for ln in item.links:
                yield (
                    ln.attrs.get('href')
                    or ln.attrs.get('ic-delete-from')
                    or ln.attrs.get('ic-post-to')
                )
        else:
            yield (
                item.attrs.get('href')
                or item.attrs.get('ic-delete-from')
                or item.attrs.get('ic-post-to')
            )


def test_agency_collection_layout():
    request = DummyRequest()
    model = ExtendedAgencyCollection(None)

    layout = AgencyCollectionLayout(model, request)
    assert layout.editbar_links is None
    assert path(layout.breadcrumbs) == 'DummyOrg/ExtendedAgencyCollection'
    assert layout.move_agency_url_template == 'AgencyMove/?csrf-token=x'

    # Add permission
    request.permissions = {'ExtendedAgencyCollection': ['Private']}
    layout = AgencyCollectionLayout(model, request)
    assert list(hrefs(layout.editbar_links)) == [
        'ExtendedAgencyCollection/create-pdf',
        'ExtendedAgencyCollection/sort',
        'ExtendedAgencyCollection/new'
    ]


def test_agency_layout():
    request = DummyRequest()
    model = ExtendedAgency('Agency')

    layout = AgencyLayout(model, request)
    assert isinstance(layout.collection, ExtendedAgencyCollection)
    assert layout.editbar_links is None
    assert path(layout.breadcrumbs) == \
        'DummyOrg/ExtendedAgencyCollection/ExtendedAgency'
    assert layout.move_agency_url_template == 'AgencyMove/?csrf-token=x'
    assert layout.move_membership_within_agency_url_template == \
        'AgencyMembershipMoveWithinAgency/?csrf-token=x'

    # Add permission
    request.permissions = {'ExtendedAgency': ['Private']}
    layout = AgencyLayout(model, request)
    assert list(hrefs(layout.editbar_links)) == [
        'AgencyProxy/edit',
        'AgencyProxy/move',
        'AgencyProxy/sort',
        'ExtendedAgency/?csrf-token=x',
        'AgencyProxy/create-pdf',
        'AgencyProxy/new',
        'AgencyProxy/new-membership',
        'AgencyProxy/sort-children?csrf-token=x',
        'AgencyProxy/sort-relationships?csrf-token=x',
    ]


def test_membership_layout():
    request = DummyRequest()
    model = AgencyMembership(agency=ExtendedAgency(title='Agency'))

    layout = MembershipLayout(model, request)
    assert layout.editbar_links is None
    assert path(layout.breadcrumbs) == \
        'DummyOrg/ExtendedAgencyCollection/ExtendedAgency/AgencyMembership'

    # Add permission
    request.permissions = {'AgencyMembership': ['Private']}
    layout = MembershipLayout(model, request)
    assert list(hrefs(layout.editbar_links)) == [
        'AgencyMembership/edit',
        'AgencyMembership/?csrf-token=x'
    ]


def test_extended_person_collection_layout():
    request = DummyRequest()
    model = ExtendedPersonCollection(None)

    layout = ExtendedPersonCollectionLayout(model, request)
    assert layout.editbar_links is None
    assert path(layout.breadcrumbs) == 'DummyOrg/#'

    # Log in as manager
    request.is_manager = True
    layout = ExtendedPersonCollectionLayout(model, request)
    assert list(hrefs(layout.editbar_links)) == [
        'ExtendedPersonCollection/create-people-xlsx',
        'ExtendedPersonCollection/new'
    ]

    # AgencyPathMixin
    root = ExtendedAgency('Root')
    child = ExtendedAgency('Child', parent=root)
    assert layout.agency_path(root) == 'Root'
    assert layout.agency_path(child) == 'Root > Child'


def test_extended_person_layout():
    request = DummyRequest()
    model = ExtendedPerson(
        first_name="Hans",
        last_name="Maulwurf",
        email="hans.maulwurf@springfield.com"
    )

    layout = ExtendedPersonLayout(model, request)
    assert layout.editbar_links is None
    assert path(layout.breadcrumbs) == \
        'DummyOrg/ExtendedPersonCollection/ExtendedPerson'

    # Add permission
    request.permissions = {'ExtendedPerson': ['Private']}
    layout = ExtendedPersonLayout(model, request)
    assert list(hrefs(layout.editbar_links)) == [
        'ExtendedPerson/edit',
        'ExtendedPerson/sort',
        'ExtendedPerson/?csrf-token=x'
    ]

    # AgencyPathMixin
    root = ExtendedAgency('Root')
    child = ExtendedAgency('Child', parent=root)
    assert layout.agency_path(root) == 'Root'
    assert layout.agency_path(child) == 'Root > Child'
