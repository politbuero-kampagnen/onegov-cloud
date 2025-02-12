from babel import Locale
from cached_property import cached_property
from decimal import Decimal
from decimal import ROUND_HALF_UP
from numbers import Integral
from onegov.core.elements import Link
from onegov.core.i18n import SiteLocale
from onegov.core.layout import ChameleonLayout
from onegov.swissvotes import _
from onegov.swissvotes.collections import SwissVoteCollection
from onegov.swissvotes.collections import TranslatablePageCollection
from onegov.swissvotes.models import TranslatablePageMove
from onegov.user import Auth


class DefaultLayout(ChameleonLayout):

    day_long_format = 'skeleton:MMMMd'
    date_long_format = 'long'
    datetime_long_format = 'medium'

    def __init__(self, model, request):
        super().__init__(model, request)
        self.request.include('frameworks')
        self.request.include('chosen')
        self.request.include('common')

        self.pages = TranslatablePageCollection(self.request.session)

    @cached_property
    def title(self):
        return ""

    @cached_property
    def top_navigation(self):
        result = [Link(_("Votes"), self.votes_url)]
        for page in self.pages.query():
            if page.id not in self.request.app.static_content_pages:
                result.append(
                    Link(
                        page.title,
                        self.request.link(page),
                        sortable_id=page.id,
                    )
                )
        return result

    @cached_property
    def editbar_links(self):
        return []

    @cached_property
    def breadcrumbs(self):
        return [Link(_("Homepage"), self.homepage_url)]

    @cached_property
    def static_path(self):
        return self.request.link(self.app.principal, 'static')

    @cached_property
    def homepage_url(self):
        return self.request.link(self.app.principal)

    @cached_property
    def disclaimer_link(self):
        page = self.pages.setdefault('disclaimer')
        return Link(page.title, self.request.link(page))

    @cached_property
    def imprint_link(self):
        page = self.pages.setdefault('imprint')
        return Link(page.title, self.request.link(page))

    @cached_property
    def data_protection_link(self):
        page = self.pages.setdefault('data-protection')
        return Link(page.title, self.request.link(page))

    @cached_property
    def votes_url(self):
        return self.request.link(SwissVoteCollection(self.request.app))

    @cached_property
    def login_url(self):
        if not self.request.is_logged_in:
            return self.request.link(
                Auth.from_request(self.request, to=self.homepage_url),
                name='login'
            )

    @cached_property
    def logout_url(self):
        if self.request.is_logged_in:
            return self.request.link(
                Auth.from_request(self.request, to=self.homepage_url),
                name='logout'
            )

    @cached_property
    def move_page_url_template(self):
        return self.csrf_protected_url(
            self.request.link(TranslatablePageMove.for_url_template())
        )

    @cached_property
    def locales(self):
        result = []
        assert self.app.locales == {'de_CH', 'fr_CH', 'en_US'}
        for locale_code in ('de_CH', 'fr_CH', 'en_US'):
            locale = Locale.parse(locale_code)
            result.append((
                locale_code,
                locale.language,
                locale.get_language_name().capitalize(),
                self.request.link(SiteLocale(locale_code, self.request.url))
            ))
        return result

    def format_policy_areas(self, vote):
        paths = {}
        for path in [area.label_path for area in vote.policy_areas]:
            paths.setdefault(path[0], [])
            paths[path[0]].append(path)

        translate = self.request.translate
        return ",<br>".join([
            "<span title=\"{}\">{}</span>".format(
                " &#10;&#10;".join([
                    " &gt; ".join([translate(part) for part in title])
                    for title in titles
                ]),
                translate(value)
            )
            for value, titles in paths.items()
        ])

    def format_bfs_number(self, number, decimal_places=None):
        """ Hide the decimal places if there are none (simple votes). """

        decimal_places = 0 if number.to_integral_value() == number else 1
        return self.format_number(number, decimal_places)

    def format_number(self, number, decimal_places=None, padding=''):
        """ Takes the given numer and formats it according to locale.

        If the number is an integer, the default decimal places are 0,
        otherwise 2.

        Overwrites parent class to use "." instead of "," for fr_CH locale
        as would be returned by babel.

        """
        if number is None:
            return ''

        if decimal_places is None:
            if isinstance(number, Integral):
                decimal_places = 0
            else:
                decimal_places = 2

        if decimal_places is not None:
            number = Decimal(number).quantize(
                Decimal(10) ** -decimal_places,
                rounding=ROUND_HALF_UP
            )

        locale = self.request.locale
        # Fixes using "," for french locale instead of "." as for german
        if locale == 'fr_CH':
            locale = 'de_CH'
        decimal, group = self.number_symbols(locale)
        result = '{{:{},.{}f}}'.format(padding, decimal_places).format(number)
        return result.translate({ord(','): group, ord('.'): decimal})
