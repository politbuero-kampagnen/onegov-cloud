from onegov.ballot import Election
from onegov.core.security import Public
from onegov.election_day import ElectionDayApp
from onegov.election_day.hidden_by_principal import \
    hide_connections_chart
from onegov.election_day.layouts import DefaultLayout
from onegov.election_day.layouts import ElectionLayout
from onegov.election_day.utils import add_last_modified_header
from onegov.election_day.utils.election import get_connection_results_api
from onegov.election_day.utils.election import get_connections_data
from sqlalchemy.orm import object_session
from onegov.election_day import _

election_incomplete_text = _(
    'The figure with the list connections will be available '
    'as soon the final results are published.'
)


@ElectionDayApp.json(
    model=Election,
    name='connections-data',
    permission=Public
)
def view_election_connections_data(self, request):

    """" View the list connections as JSON.

    Used to for the connection sankey chart.

    """
    return get_connections_data(self, request)


@ElectionDayApp.html(
    model=Election,
    name='connections-chart',
    template='embed.pt',
    permission=Public
)
def view_election_connections_chart(self, request):

    """" View the connections as sankey chart. """

    @request.after
    def add_last_modified(response):
        add_last_modified_header(response, self.last_modified)

    skip_rendering = hide_connections_chart(self, request)

    return {
        'model': self,
        'layout': DefaultLayout(self, request),
        'type': 'connections-chart',
        'skip_rendering': skip_rendering,
        'help_text': election_incomplete_text
    }


@ElectionDayApp.html(
    model=Election,
    name='connections-table',
    template='embed.pt',
    permission=Public
)
def view_election_connections_table(self, request):

    """" View the connections tables as widget. """

    @request.after
    def add_last_modified(response):
        add_last_modified_header(response, self.last_modified)

    return {
        'model': self,
        'layout': DefaultLayout(self, request),
        'connections': get_connection_results_api(self, object_session(self)),
        'type': 'election-table',
        'scope': 'connections'
    }


@ElectionDayApp.html(
    model=Election,
    name='connections',
    template='election/connections.pt',
    permission=Public
)
def view_election_connections(self, request):

    """" The main view. """

    layout = ElectionLayout(self, request, 'connections')
    return {
        'election': self,
        'layout': layout,
        'connections': get_connection_results_api(self, object_session(self)),
        'skip_rendering': hide_connections_chart(self, request),
        'help_text': election_incomplete_text,
    }


@ElectionDayApp.svg_file(model=Election, name='connections-svg')
def view_election_connections_svg(self, request):

    """ View the connections as SVG. """

    layout = ElectionLayout(self, request, 'connections')
    return {
        'path': layout.svg_path,
        'name': layout.svg_name
    }
