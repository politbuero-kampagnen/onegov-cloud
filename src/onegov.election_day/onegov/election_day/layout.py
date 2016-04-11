from babel import Locale
from cached_property import cached_property
from datetime import datetime
from onegov.core.i18n import SiteLocale
from onegov.core.layout import ChameleonLayout
from onegov.core.static import StaticFile
from onegov.election_day.models import Archive, Manage
from onegov.user import Auth


class Layout(ChameleonLayout):

    def __init__(self, request, model):
        super().__init__(request, model)
        self.request.include('common')

    @cached_property
    def principal(self):
        return self.request.app.principal

    @cached_property
    def homepage_link(self):
        return self.request.link(self.principal)

    @cached_property
    def opendata_link(self):
        return self.request.link(self.principal, 'opendata')

    @cached_property
    def font_awesome_path(self):
        static_file = StaticFile.from_application(
            self.app, 'font-awesome/css/font-awesome.min.css')

        return self.request.link(static_file)

    def get_topojson_link(self, canton, year):
        return self.request.link(
            StaticFile('mapdata/{}/{}.json'.format(year, canton)))

    @cached_property
    def copyright_year(self):
        return datetime.utcnow().year

    @cached_property
    def manage_link(self):
        return self.request.link(Manage(self.app.session()))

    @cached_property
    def login_link(self):
        if not self.request.is_logged_in:
            return self.request.link(
                Auth.from_request(self.request, to=self.manage_link),
                name='login'
            )

    @cached_property
    def logout_link(self):
        if self.request.is_logged_in:
            return self.request.link(
                Auth.from_request(self.request), name='logout')

    @cached_property
    def archive(self):
        return Archive(self.request.app.session())

    @cached_property
    def locales(self):
        to = self.request.url

        def get_name(locale):
            return Locale.parse(locale).get_language_name().capitalize()

        def get_link(locale):
            return self.request.link(SiteLocale(locale, to))

        return [
            (get_name(locale), get_link(locale))
            for locale in sorted(self.app.locales)
        ]


class DefaultLayout(Layout):
    pass


class ManageLayout(DefaultLayout):
    pass

    def __init__(self, request, model):
        super().__init__(request, model)
        self.request.include('form')
