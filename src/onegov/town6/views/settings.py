""" The settings view, defining things like the logo or color of the org. """
from onegov.core.security import Secret
from onegov.org import _
from onegov.town.views.settings import get_custom_settings_form
from onegov.town6.forms.settings import GeneralSettingsForm

from onegov.org.forms.settings import FaviconSettingsForm, LinksSettingsForm, \
    HeaderSettingsForm, FooterSettingsForm, ModuleSettingsForm, \
    MapSettingsForm, AnalyticsSettingsForm, HolidaySettingsForm, \
    OrgTicketSettingsForm
from onegov.org.models import Organisation
from onegov.org.views.settings import (
    handle_homepage_settings, view_settings,
    handle_ticket_settings, preview_holiday_settings, handle_general_settings,
    handle_favicon_settings, handle_links_settings, handle_header_settings,
    handle_footer_settings, handle_module_settings, handle_map_settings,
    handle_analytics_settings, handle_holiday_settings)

from onegov.town6.app import TownApp

from onegov.town6.layout import SettingsLayout, DefaultLayout


@TownApp.html(
    model=Organisation, name='settings', template='settings.pt',
    permission=Secret)
def view_town_settings(self, request):
    return view_settings(self, request, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='general-settings', template='form.pt',
    permission=Secret, form=GeneralSettingsForm, setting=_("General"),
    icon='fa-cogs', order=-1000)
def town_handle_general_settings(self, request, form):
    return handle_general_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='favicon-settings', template='form.pt',
    permission=Secret, form=FaviconSettingsForm, setting=_("Favicon"),
    icon='fas fa-external-link-square-alt', order=-990)
def town_handle_favicon_settings(self, request, form):
    return handle_favicon_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='link-settings', template='form.pt',
    permission=Secret, form=LinksSettingsForm, setting=_("Links"),
    icon='fa-link', order=-980)
def town_handle_links_settings(self, request, form):
    return handle_links_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='header-settings', template='form.pt',
    permission=Secret, form=HeaderSettingsForm, setting=_("Header"),
    icon='fa-window-maximize', order=-810)
def town_handle_header_settings(self, request, form):
    return handle_header_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='footer-settings', template='form.pt',
    permission=Secret, form=FooterSettingsForm, setting=_("Footer"),
    icon='fa-window-minimize', order=-800)
def town_handle_footer_settings(self, request, form):
    return handle_footer_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='module-settings', template='form.pt',
    permission=Secret, form=ModuleSettingsForm, setting=_("Modules"),
    icon='fa-sitemap', order=-700)
def town_handle_module_settings(self, request, form):
    return handle_module_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='map-settings', template='form.pt',
    permission=Secret, form=MapSettingsForm, setting=_("Map"),
    icon='fa-map-marker-alt', order=-700)
def town_handle_map_settings(self, request, form):
    return handle_map_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='analytics-settings', template='form.pt',
    permission=Secret, form=AnalyticsSettingsForm, setting=_("Analytics"),
    icon='fa-chart-bar ', order=-600)
def town_handle_analytics_settings(self, request, form):
    return handle_analytics_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='holiday-settings', template='form.pt',
    permission=Secret, form=HolidaySettingsForm, setting=_("Holidays"),
    icon='fa-calendar', order=-500)
def town_handle_holiday_settings(self, request, form):
    return handle_holiday_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(
    model=Organisation, name='ticket-settings', template='form.pt',
    permission=Secret, form=OrgTicketSettingsForm,
    setting=_("Ticket Settings"), order=-950, icon='fa-ticket-alt'
)
def town_handle_ticket_settings(self, request, form):
    return handle_ticket_settings(
        self, request, form, SettingsLayout(self, request))


@TownApp.form(model=Organisation, name='holiday-settings-preview',
              permission=Secret, form=HolidaySettingsForm)
def town_preview_holiday_settings(self, request, form):
    return preview_holiday_settings(
        self, request, form, DefaultLayout(self, request))


@TownApp.form(model=Organisation, name='homepage-settings', template='form.pt',
              permission=Secret, form=get_custom_settings_form,
              setting=_("Homepage"), icon='fa-home', order=-900)
def custom_handle_settings(self, request, form):

    form.delete_field('homepage_cover')
    form.delete_field('redirect_homepage_to')
    form.delete_field('redirect_path')

    return handle_homepage_settings(
        self, request, form, SettingsLayout(self, request))
