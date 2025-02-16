""" Contains the base application used by other applications. """

from chameleon import PageTemplate
from collections import defaultdict
from dectate import directive
from more.content_security import SELF
from onegov.core import Framework, utils
from onegov.core.framework import default_content_security_policy
from onegov.core.i18n import default_locale_negotiator
from onegov.core.orm import orm_cached
from onegov.core.widgets import transform_structure
from onegov.file import DepotApp
from onegov.form import FormApp
from onegov.gis import MapboxApp
from onegov.org import directives
from onegov.org.initial_content import create_new_organisation
from onegov.org.models import Dashboard
from onegov.org.models import Topic, Organisation, PublicationCollection
from onegov.org.request import OrgRequest
from onegov.org.theme import OrgTheme
from onegov.page import Page, PageCollection
from onegov.pay import PayApp
from onegov.reservation import LibresIntegration
from onegov.search import ElasticsearchApp
from onegov.ticket import TicketCollection
from onegov.ticket import TicketPermission
from onegov.user import UserApp
from purl import URL
from sqlalchemy import desc


class OrgApp(Framework, LibresIntegration, ElasticsearchApp, MapboxApp,
             DepotApp, PayApp, FormApp, UserApp):

    serve_static_files = True
    request_class = OrgRequest

    #: org directives
    homepage_widget = directive(directives.HomepageWidgetAction)
    export = directive(directives.ExportAction)
    userlinks = directive(directives.UserlinkAction)
    directory_search_widget = directive(directives.DirectorySearchWidgetAction)
    settings_view = directive(directives.SettingsView)
    boardlet = directive(directives.Boardlet)

    #: cronjob settings
    send_daily_ticket_statistics = True

    def is_allowed_application_id(self, application_id):
        """ Stops onegov.server from ever passing the request to the org
        application, if the schema does not exist. This way we can host
        onegov.org in a way that allows all requests to ``*.example.org``.

        If the schema for ``newyork.example.org`` exists, the request is
        handled. If the schema does not exist, the request is not handled.

        Here we basically decide if an org exists or not.

        """
        schema = self.namespace + '-' + application_id

        if schema in self.known_schemas:
            return True

        # block invalid schemas from ever being checked
        if not self.session_manager.is_valid_schema(schema):
            return False

        # if the schema exists, remember it
        if self.session_manager.is_schema_found_on_database(schema):
            self.known_schemas.add(schema)

            return True

        return False

    def configure_application(self, **cfg):
        super().configure_application(**cfg)
        self.known_schemas = set()

        if self.has_database_connection:
            schema_prefix = self.namespace + '-'

            self.known_schemas = set(
                s for s in self.session_manager.list_schemas()
                if s.startswith(schema_prefix)
            )

    def configure_organisation(self, **cfg):
        self.enable_user_registration = cfg.get(
            'enable_user_registration',
            False
        )
        self.enable_yubikey = cfg.get('enable_yubikey', False)
        self.disable_password_reset = cfg.get('disable_password_reset', False)

    @orm_cached(policy='on-table-change:organisations')
    def org(self):
        return self.session().query(Organisation).first()

    @orm_cached(policy='on-table-change:pages')
    def root_pages(self):
        query = PageCollection(self.session()).query(ordered=False)
        query = query.order_by(desc(Page.type), Page.order)
        query = query.filter(Page.parent_id == None)

        def include(page):
            if page.type != 'news':
                return True

            return page.children and True or False

        return tuple(p for p in query if include(p))

    @orm_cached(policy='on-table-change:organisations')
    def homepage_template(self):
        structure = self.org.meta.get('homepage_structure')
        if structure:
            widgets = self.config.homepage_widget_registry.values()
            return PageTemplate(transform_structure(widgets, structure))
        else:
            return PageTemplate('')

    @orm_cached(policy='on-table-change:tickets')
    def ticket_count(self):
        return TicketCollection(self.session()).get_count()

    @orm_cached(policy='on-table-change:ticket_permissions')
    def ticket_permissions(self):
        result = {}
        for permission in self.session().query(TicketPermission):
            handler = result.setdefault(permission.handler_code, {})
            group = handler.setdefault(permission.group, [])
            group.append(permission.user_group_id.hex)
        return result

    @orm_cached(policy='on-table-change:pages')
    def homepage_pages(self):
        pages = PageCollection(self.session()).query()
        pages = pages.filter(Topic.type == 'topic')
        pages = pages.filter(Topic.meta['is_visible_on_homepage'] == True)

        result = defaultdict(list)

        for page in pages.all():
            if page.is_visible_on_homepage:
                result[page.root.id].append(page)

        for key in result:
            result[key] = list(sorted(
                result[key],
                key=lambda p: utils.normalize_for_url(p.title)
            ))

        return result

    @orm_cached(policy='on-table-change:files')
    def publications_count(self):
        return PublicationCollection(self.session()).query().count()

    def send_email(self, **kwargs):
        """ Wraps :meth:`onegov.core.framework.Framework.send_email`, setting
        the reply_to address by using the reply address from the organisation
        settings.

        """
        category = kwargs.get('category', 'marketing')

        reply_to = kwargs.pop('reply_to', self.org.meta.get('reply_to', None))
        reply_to = reply_to or self.mail[category]['sender']
        reply_to = "{} <{}>".format(self.org.title, reply_to)

        return super().send_email(reply_to=reply_to, **kwargs)

    @property
    def theme_options(self):
        return self.org.theme_options or {}

    @property
    def font_family(self):
        return self.theme_options.get('font-family-sans-serif')

    def checkout_button(self, button_label, title, price, email, locale):
        provider = self.default_payment_provider

        if not provider:
            return None

        checkout = {
            'label': button_label,
            'amount': price and price.amount,
            'currency': price and price.currency,
            'email': email,
            'name': self.org.name,
            'description': title,
            'locale': locale.split('_')[0],
            'allowRememberMe': 'false'
        }

        if self.org.square_logo_url:
            checkout['image'] = self.org.square_logo_url

        return provider.checkout_button(**checkout)

    def redirect_after_login(self, identity, request, default):
        """ Returns the path to redirect after login, given the request and
        the default login path, which is usually the current path.

        Returns a path or None, if the default should be used.

        """

        # if we already have a target, we do not change it
        if default != '/':
            return None

        # we redirect to the dashboard…
        dashboard = Dashboard(request)

        # …if available…
        if not dashboard.is_available:
            return None

        # …and accessible…
        permission = self.permission_by_view(dashboard, view_name=None)

        if not self._permits(identity, dashboard, permission):
            return None

        return URL(request.link(dashboard)).path()


@OrgApp.webasset_path()
def get_shared_assets_path():
    return utils.module_path('onegov.shared', 'assets/js')


@OrgApp.setting(section='i18n', name='locales')
def get_i18n_used_locales():
    return {'de_CH', 'fr_CH'}


@OrgApp.setting(section='i18n', name='localedirs')
def get_i18n_localedirs():
    return [
        utils.module_path('onegov.org', 'locale'),
        utils.module_path('onegov.form', 'locale'),
        utils.module_path('onegov.user', 'locale')
    ]


@OrgApp.setting(section='i18n', name='default_locale')
def get_i18n_default_locale():
    return 'de_CH'


@OrgApp.setting(section='i18n', name='locale_negotiator')
def get_locale_negotiator():
    def locale_negotiator(locales, request):
        if request.app.org:
            locales = request.app.org.locales or get_i18n_default_locale()

            if isinstance(locales, str):
                locales = (locales, )

            return default_locale_negotiator(locales, request) or locales[0]
        else:
            return default_locale_negotiator(locales, request)
    return locale_negotiator


@OrgApp.static_directory()
def get_static_directory():
    return 'static'


@OrgApp.template_directory()
def get_template_directory():
    return 'templates'


@OrgApp.setting(section='core', name='theme')
def get_theme():
    return OrgTheme()


@OrgApp.setting(section='content_security_policy', name='default')
def org_content_security_policy():
    policy = default_content_security_policy()

    policy.child_src.add(SELF)
    policy.child_src.add('https://*.youtube.com')
    policy.child_src.add('https://*.vimeo.com')
    policy.child_src.add('https://checkout.stripe.com')
    policy.child_src.add('https://onegov-livechat.herokuapp.com')

    policy.connect_src.add(SELF)
    policy.connect_src.add('https://checkout.stripe.com')
    policy.connect_src.add('https://sentry.io')
    policy.connect_src.add('https://*.google-analytics.com')
    policy.connect_src.add('https://stats.g.doubleclick.net')
    policy.connect_src.add('https://maps.zg.ch')
    policy.connect_src.add('https://api.mapbox.com')
    policy.connect_src.add('https://stats.seantis.ch')

    return policy


@OrgApp.setting(section='org', name='create_new_organisation')
def get_create_new_organisation_factory():
    return create_new_organisation


@OrgApp.setting(section='org', name='status_mail_roles')
def get_status_mail_roles():
    return ('admin', 'editor')


@OrgApp.setting(section='org', name='ticket_manager_roles')
def get_ticket_manager_roles():
    return ('admin', 'editor')


@OrgApp.setting(section='org', name='require_complete_userprofile')
def get_require_complete_userprofile():
    return False


@OrgApp.setting(section='org', name='is_complete_userprofile')
def get_is_complete_userprofile_handler():
    def is_complete_userprofile(request, username):
        return True

    return is_complete_userprofile


@OrgApp.setting(section='org', name='default_directory_search_widget')
def get_default_directory_search_widget():
    return None


@OrgApp.setting(section='org', name='public_ticket_messages')
def get_public_ticket_messages():
    """ Returns a list of message types which are availble on the ticket
    status page, visible to anyone that knows the unguessable url.

    """

    # do *not* add ticket_note here, those are private!
    return (
        'directory',
        'event',
        'payment',
        'reservation',
        'submission',
        'ticket',
        'ticket_chat',
    )


@OrgApp.webasset_path()
def get_js_path():
    return 'assets/js'


@OrgApp.webasset_path()
def get_css_path():
    return 'assets/css'


@OrgApp.webasset_output()
def get_webasset_output():
    return 'assets/bundles'


@OrgApp.webasset('sortable')
def get_sortable_asset():
    yield 'sortable.js'
    yield 'sortable_custom.js'


@OrgApp.webasset('fullcalendar')
def get_fullcalendar_asset():
    yield 'fullcalendar.css'
    yield 'fullcalendar.js'
    yield 'fullcalendar.de.js'
    yield 'fullcalendar.fr.js'
    yield 'reservationcalendar.jsx'
    yield 'reservationcalendar_custom.js'


@OrgApp.webasset('code_editor')
def get_code_editor_asset():
    yield 'ace.js'
    yield 'ace-mode-form.js'
    yield 'ace-mode-markdown.js'
    yield 'ace-mode-xml.js'
    yield 'ace-mode-yaml.js'
    yield 'ace-theme-tomorrow.js'
    yield 'formcode'
    yield 'code_editor.js'


@OrgApp.webasset('editor')
def get_editor_asset():
    yield 'bufferbuttons.js'
    yield 'definedlinks.js'
    yield 'filemanager.js'
    yield 'imagemanager.js'
    yield 'redactor.de.js'
    yield 'redactor.fr.js'
    yield 'redactor.it.js'
    yield 'input_with_button.js'
    yield 'editor.js'


@OrgApp.webasset('timeline')
def get_timeline_asset():
    yield 'timeline.jsx'


# do NOT minify the redactor, or the copyright notice goes away, which
# is something we are not allowed to do per our license
@OrgApp.webasset('redactor', filters={'js': None})
def get_redactor_asset():
    yield 'redactor.js'
    yield 'redactor.css'


@OrgApp.webasset('upload')
def get_upload_asset():
    yield 'upload.js'


@OrgApp.webasset('editalttext')
def get_editalttext_asset():
    yield 'editalttext.js'


@OrgApp.webasset('prompt')
def get_prompt():
    yield 'prompt.jsx'


@OrgApp.webasset('photoswipe')
def get_photoswipe_asset():
    yield 'photoswipe.css'
    yield 'photoswipe-skin.css'
    yield 'photoswipe.js'
    yield 'photoswipe-ui.js'
    yield 'photoswipe-custom.js'


@OrgApp.webasset('tags-input')
def get_tags_input():
    yield 'tags-input.js'
    yield 'tags-input-setup.js'


@OrgApp.webasset('filedigest')
def get_filehash():
    yield 'asmcrypto-lite.js'
    yield 'filedigest.js'


@OrgApp.webasset('many')
def get_many():
    yield 'many.jsx'


@OrgApp.webasset('monthly-view')
def get_monthly_view():
    yield 'daypicker.js'
    yield 'monthly-view.jsx'


@OrgApp.webasset('common')
def get_common_asset():
    yield 'global.js'
    yield 'polyfills.js'
    yield 'jquery.datetimepicker.css'
    yield 'locale.js'
    yield 'modernizr.js'
    yield 'clipboard.js'
    yield 'jquery.js'
    yield 'foundation.js'
    yield 'foundation.alert.js'
    yield 'foundation.dropdown.js'
    yield 'foundation.orbit.js'
    yield 'foundation.reveal.js'
    yield 'foundation.topbar.js'
    yield 'intercooler.js'
    yield 'underscore.js'
    yield 'react.js'
    yield 'react-dom.js'
    yield 'form_dependencies.js'
    yield 'confirm.jsx'
    yield 'typeahead.jsx'
    yield 'pay'
    yield 'moment.js'
    yield 'moment.de-ch.js'
    yield 'moment.fr-ch.js'
    yield 'jquery.datetimepicker.js'
    yield 'jquery.mousewheel.js'
    yield 'jquery.popupoverlay.js'
    yield 'jquery.load.js'
    yield 'videoframe.js'
    yield 'datetimepicker.js'
    yield 'url.js'
    yield 'date-range-selector.js'
    yield 'lazyalttext.js'
    yield 'lazysizes.js'
    yield 'toggle.js'
    yield 'common.js'
    yield '_blank.js'
    yield 'forms.js'
    yield 'internal_link_check.js'
    yield 'tickets.js'
    yield 'items_selectable.js'


@OrgApp.webasset('accordion')
def get_accordion_asset():
    yield 'foundation.accordion.js'


@OrgApp.webasset('fontpreview')
def get_fontpreview_asset():
    yield 'fontpreview.js'


@OrgApp.webasset('scroll-to-username')
def get_scroll_to_username_asset():
    yield 'scroll_to_username.js'


@OrgApp.webasset('all_blank')
def get_all_blank_asset():
    yield 'all_blank.js'
