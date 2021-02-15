from onegov.core.security import Private
from onegov.org.views.export import view_export_collection, view_export
from onegov.town6 import TownApp, _
from onegov.org.models import Export, ExportCollection


@TownApp.html(
    model=ExportCollection,
    permission=Private,
    template='exports.pt')
def town_view_export_collection(self, request):
    return view_export_collection(self, request)


@TownApp.form(
    model=Export,
    permission=Private,
    template='export.pt',
    form=lambda model, request: model.form_class)
def town_view_export(self, request, form):
    return view_export(self, request, form)
