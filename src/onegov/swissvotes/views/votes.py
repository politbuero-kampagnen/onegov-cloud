from morepath.request import Response
from onegov.core.security import Private
from onegov.core.security import Public
from onegov.core.security import Secret
from onegov.form import Form
from onegov.swissvotes import _
from onegov.swissvotes import SwissvotesApp
from onegov.swissvotes.collections import SwissVoteCollection
from onegov.swissvotes.external_resources import MfgPosters
from onegov.swissvotes.external_resources import SaPosters
from onegov.swissvotes.forms import SearchForm
from onegov.swissvotes.forms import UpdateDatasetForm
from onegov.swissvotes.forms import UpdateExternalResourcesForm
from onegov.swissvotes.layouts import DeleteVotesLayout
from onegov.swissvotes.layouts import UpdateExternalResourcesLayout
from onegov.swissvotes.layouts import UpdateVotesLayout
from onegov.swissvotes.layouts import VotesLayout
from translationstring import TranslationString


@SwissvotesApp.form(
    model=SwissVoteCollection,
    permission=Public,
    form=SearchForm,
    template='votes.pt'
)
def view_votes(self, request, form):
    if not form.errors:
        form.apply_model(self)

    return {
        'layout': VotesLayout(self, request),
        'form': form
    }


@SwissvotesApp.form(
    model=SwissVoteCollection,
    permission=Private,
    form=UpdateDatasetForm,
    template='form.pt',
    name='update'
)
def update_votes(self, request, form):
    self = self.default()

    layout = UpdateVotesLayout(self, request)

    if form.submitted(request):
        added, updated = self.update(form.dataset.data)
        request.message(
            _(
                "Dataset updated (${added} added, ${updated} updated)",
                mapping={'added': added, 'updated': updated}
            ),
            'success'
        )

        # Warn if descriptor labels are missing
        missing = set()
        for vote in self.query():
            for policy_area in vote.policy_areas:
                missing |= set(
                    path for path in policy_area.label_path
                    if not isinstance(path, TranslationString)
                )
        if missing:
            request.message(
                _(
                    "The dataset contains unknown descriptors: ${items}.",
                    mapping={'items': ', '.join(sorted(missing))}
                ),
                'warning'
            )

        return request.redirect(layout.votes_url)

    return {
        'layout': layout,
        'form': form,
        'cancel': request.link(self),
        'button_text': _("Update"),
    }


@SwissvotesApp.form(
    model=SwissVoteCollection,
    permission=Private,
    form=UpdateExternalResourcesForm,
    template='form.pt',
    name='update-external-resources'
)
def update_external_resources(self, request, form):
    self = self.default()

    layout = UpdateExternalResourcesLayout(self, request)

    if form.submitted(request):
        added_total = 0
        updated_total = 0
        removed_total = 0
        failed_total = set()
        for resource, cls in (
            ('mfg', MfgPosters(request.app.mfg_api_token)),
            ('sa', SaPosters())
        ):
            if resource in form.resources.data:
                added, updated, removed, failed = cls.fetch(request.session)
                added_total += added
                updated_total += updated
                removed_total += removed
                failed_total |= failed

        request.message(
            _(
                'External resources updated (${added} added, '
                '${updated} updated, ${removed} removed)',
                mapping={
                    'added': added_total,
                    'updated': updated_total,
                    'removed': removed_total
                }
            ),
            'success'
        )
        if failed_total:
            failed_total = ', '.join((
                layout.format_bfs_number(item) for item in sorted(failed_total)
            ))
            request.message(
                _(
                    'Some external resources could not be updated: ${failed}',
                    mapping={'failed': failed_total}
                ),
                'warning'
            )

        return request.redirect(layout.votes_url)

    return {
        'layout': layout,
        'form': form,
        'cancel': request.link(self),
        'button_text': _("Update external resources"),
    }


@SwissvotesApp.view(
    model=SwissVoteCollection,
    permission=Public,
    name='csv'
)
def export_votes_csv(self, request):
    return Response(
        request.app.get_cached_dataset('csv'),
        content_type='text/csv',
        content_disposition='inline; filename=dataset.csv'
    )


@SwissvotesApp.view(
    model=SwissVoteCollection,
    permission=Public,
    name='xlsx'
)
def export_votes_xlsx(self, request):
    return Response(
        request.app.get_cached_dataset('xlsx'),
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ),
        content_disposition='inline; filename=dataset.xlsx'
    )


@SwissvotesApp.form(
    model=SwissVoteCollection,
    permission=Secret,
    form=Form,
    template='form.pt',
    name='delete'
)
def delete_votes(self, request, form):
    self = self.default()

    layout = DeleteVotesLayout(self, request)

    if form.submitted(request):
        for vote in self.query():
            request.session.delete(vote)
        request.message(_("All votes deleted"), 'success')
        return request.redirect(layout.votes_url)

    return {
        'layout': layout,
        'form': form,
        'message': _("Do you really want to delete all votes?!"),
        'button_text': _("Delete"),
        'button_class': 'alert',
        'cancel': request.link(self)
    }


@SwissvotesApp.view(
    model=SwissVoteCollection,
    permission=Public,
    name='timeline'
)
def view_timeline(self, request):

    def calculate_points_in_time(vote):
        result = {
            's': None,  # Sammelbeginn
            'e': None,  # Einreichung
            'b': None,  # Bundesrätliche Botschaft
            'p': None,  # Parlamentsbeschluss
            'f': None,  # Zustandekommen Fakultatives Referendum
        }

        # Einreichung
        if vote.duration_initative_total is not None:
            result['e'] = vote.duration_initative_total

        # Sammelbeginn
        if vote.duration_initative_collection is not None:
            assert result['e'] is not None
            result['s'] = result['e'] + vote.duration_initative_collection
        # Bundesrätlichee Botschaft
        if (
            vote.duration_post_federal_assembly is not None
            and vote.duration_federal_assembly is not None
        ):
            result['b'] = (
                vote.duration_post_federal_assembly
                + vote.duration_federal_assembly
            )
        if vote.duration_referendum_total is not None:
            if result['b'] and result['b'] != vote.duration_referendum_total:
                print('Warning: Inconsistent values')
            result['b'] = vote.duration_referendum_total

        if vote.duration_initative_federal_council is not None:
            value = result['e'] - vote.duration_initative_federal_council
            if result['b'] and result['b'] != value:
                print('Warning: Inconsistent values')
            result['b'] = value

        # Parlamentsbeschluss
        if vote.duration_post_federal_assembly is not None:
            result['p'] = vote.duration_post_federal_assembly

        # Zustandekommen Fakultatives Referendum
        if vote.duration_referendum_collection is not None:
            assert result['p'] is not None
            result['f'] = result['p'] - vote.duration_referendum_collection

        return result

    result = []
    for vote in self.query():
        times = calculate_points_in_time(vote)
        scale = 10
        length = max((value or 0 for value in times.values())) // scale + 1
        line = length * ['.']
        for key, value in times.items():
            if value:
                line[value // scale] = key.upper()
        result.append(''.join(reversed(line)) + f' {vote.date}')

    # align right
    length = max((len(line) for line in result))
    result = [line.rjust(length, ' ') for line in result]
    return Response(
        '\n'.join(result),
        content_type='text/plain',
    )
