from onegov.ballot import ElectionCompound
from onegov.core.security import Public
from onegov.election_day import ElectionDayApp
from onegov.election_day.layouts import ElectionCompoundLayout
from onegov.election_day.utils.election import get_elected_candidates


def get_districts(model, layout):
    return {
        election.id: (
            layout.election_title(election),
            layout.request.link(election)
        )
        for election in layout.model.elections if election.results.first()
    }


@ElectionDayApp.html(
    model=ElectionCompound,
    name='candidates',
    template='election_compound/candidates.pt',
    permission=Public
)
def view_election_compound_candidates(self, request):

    """" The main view. """

    session = request.app.session()
    layout = ElectionCompoundLayout(self, request, 'candidates')

    return {
        'election_compound': self,
        'elected_candidates': get_elected_candidates(self, session),
        'districts': get_districts(self, layout),
        'layout': layout
    }


@ElectionDayApp.html(
    model=ElectionCompound,
    name='candidates-table',
    template='embed.pt',
    permission=Public
)
def view_election_statistics_table(self, request):

    """" View for the standalone statistics table.  """

    session = request.app.session()
    layout = ElectionCompoundLayout(self, request, 'candidates')

    return {
        'election_compound': self,
        'elected_candidates': get_elected_candidates(self, session),
        'districts': get_districts(self, layout),
        'layout': layout,
        'type': 'election-compound-table',
        'scope': 'candidates'
    }
