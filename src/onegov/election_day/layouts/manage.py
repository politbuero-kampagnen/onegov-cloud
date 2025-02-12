from cached_property import cached_property
from onegov.ballot import ElectionCollection
from onegov.ballot import ElectionCompoundCollection
from onegov.ballot import VoteCollection
from onegov.election_day import _
from onegov.election_day.collections import DataSourceCollection
from onegov.election_day.collections import DataSourceItemCollection
from onegov.election_day.collections import EmailSubscriberCollection
from onegov.election_day.collections import ScreenCollection
from onegov.election_day.collections import SmsSubscriberCollection
from onegov.election_day.collections import SubscriberCollection
from onegov.election_day.collections import UploadTokenCollection
from onegov.election_day.layouts.default import DefaultLayout
from onegov.election_day.models import EmailSubscriber
from onegov.election_day.models import SmsSubscriber


class ManageLayout(DefaultLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(self.model)

    @cached_property
    def menu(self):
        session = self.request.session
        principal = self.principal

        result = []
        result.append((
            _("Votes"),
            self.request.link(VoteCollection(session)),
            isinstance(self.model, VoteCollection),
            []
        ))

        submenu = []
        submenu.append((
            _("Elections"),
            self.request.link(ElectionCollection(session)),
            isinstance(self.model, ElectionCollection),
            []
        ))
        submenu.append((
            _("Compounds of elections"),
            self.request.link(ElectionCompoundCollection(session)),
            isinstance(self.model, ElectionCompoundCollection),
            []
        ))
        result.append((
            _("Elections"),
            '',
            (
                isinstance(self.model, ElectionCollection)
                or isinstance(self.model, ElectionCompoundCollection)
            ),
            submenu
        ))

        submenu = []
        submenu.append((
            _("Upload tokens"),
            self.request.link(UploadTokenCollection(session)),
            isinstance(self.model, UploadTokenCollection),
            []
        ))
        if principal.wabsti_import:
            submenu.append((
                _("Wabsti data sources"),
                self.request.link(DataSourceCollection(session)),
                (
                    isinstance(self.model, DataSourceCollection)
                    or isinstance(self.model, DataSourceItemCollection)
                ),
                []
            ))
        result.append((
            _("Import configuration"),
            '',
            (
                isinstance(self.model, UploadTokenCollection)
                or isinstance(self.model, DataSourceCollection)
                or isinstance(self.model, DataSourceItemCollection)
            ),
            submenu
        ))

        if self.principal.notifications:
            submenu = []
            if principal.sms_notification:
                submenu.append((
                    _("SMS subscribers"),
                    self.request.link(SmsSubscriberCollection(session)),
                    isinstance(self.model, SmsSubscriberCollection),
                    []
                ))
            if self.principal.email_notification:
                submenu.append((
                    _("Email subscribers"),
                    self.request.link(EmailSubscriberCollection(session)),
                    isinstance(self.model, EmailSubscriberCollection),
                    []
                ))
            submenu.append((
                _("Trigger notifications"),
                self.request.link(
                    self.principal, name='trigger-notifications'
                ),
                'trigger-notifications' in self.request.url,
                []
            ))
            result.append((
                _("Subscribers"),
                '',
                (
                    isinstance(self.model, SmsSubscriberCollection)
                    or isinstance(self.model, EmailSubscriberCollection)
                ),
                submenu
            ))

        result.append((
            _("Screens"),
            self.request.link(ScreenCollection(session)),
            isinstance(self.model, ScreenCollection),
            []
        ))

        if self.request.is_secret(self.model):
            submenu = [
                (
                    _("Update archived results"),
                    self.request.link(self.principal, 'update-results'),
                    'update-results' in self.request.url,
                    []
                ),
                (
                    _("Clear cache"),
                    self.request.link(self.principal, 'clear-cache'),
                    'clear-cache' in self.request.url,
                    []
                )
            ]

            result.append((
                _("Administration"),
                '',
                False,
                submenu
            ))

        return result

    def title(self):
        try:
            return self.breadcrumbs[-1][0]
        except (IndexError, TypeError):
            return ''

    def __init__(self, model, request):
        super().__init__(model, request)
        self.request.include('backend_common')
        self.request.include('chosen')
        self.breadcrumbs = [
            (_("Manage"), super().manage_link, 'unavailable'),
        ]


class ManageElectionsLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(
            ElectionCollection(self.request.session)
        )

    def __init__(self, model, request):
        super().__init__(model, request)
        self.breadcrumbs.append(
            (_("Elections"), request.link(self.model), '')
        )


class ManageElectionCompoundsLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(
            ElectionCompoundCollection(self.request.session)
        )

    def __init__(self, model, request):
        super().__init__(model, request)
        self.breadcrumbs.append(
            (_("Compounds of elections"), request.link(self.model), '')
        )


class ManageVotesLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(
            VoteCollection(self.request.session)
        )

    def __init__(self, model, request):
        super().__init__(model, request)
        self.breadcrumbs.append(
            (_("Votes"), request.link(self.model), ''),
        )


class ManageSubscribersLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        if isinstance(self.model, SubscriberCollection):
            return self.request.link(self.model)

        if isinstance(self.model, SmsSubscriber):
            return self.request.link(
                SmsSubscriberCollection(self.request.session)
            )
        elif isinstance(self.model, EmailSubscriber):
            return self.request.link(
                EmailSubscriberCollection(self.request.session)
            )

        raise NotImplementedError()

    def __init__(self, model, request):
        super().__init__(model, request)
        if isinstance(self.model, EmailSubscriberCollection):
            self.breadcrumbs.append(
                (_("Email subscribers"), request.link(self.model), ''),
            )
        elif isinstance(self.model, SmsSubscriberCollection):
            self.breadcrumbs.append(
                (_("SMS subscribers"), request.link(self.model), ''),
            )
        else:
            self.breadcrumbs.append(
                (_("Subscribers"), request.link(self.model), ''),
            )


class ManageUploadTokensLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(
            UploadTokenCollection(self.request.session)
        )

    def __init__(self, model, request):
        super().__init__(model, request)
        self.breadcrumbs.append(
            (_("Upload tokens"), request.link(self.model), ''),
        )


class ManageDataSourcesLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(
            DataSourceCollection(self.request.session)
        )

    def __init__(self, model, request):
        super().__init__(model, request)
        self.breadcrumbs.append(
            (_("Wabsti data sources"), request.link(self.model), ''),
        )


class ManageDataSourceItemsLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(
            DataSourceItemCollection(
                self.request.session,
                self.model.id
            )
        )

    def __init__(self, model, request):
        super().__init__(model, request)
        self.breadcrumbs.append(
            (
                _("Wabsti data sources"),
                self.request.link(
                    DataSourceCollection(self.request.session)
                ),
                ''
            ),
        )
        self.breadcrumbs.append(
            (_("Mappings"), request.link(self.model), ''),
        )


class ManageScreensLayout(ManageLayout):

    @cached_property
    def manage_model_link(self):
        return self.request.link(
            ScreenCollection(self.request.session)
        )

    def __init__(self, model, request):
        super().__init__(model, request)
        self.breadcrumbs.append(
            (_("Screens"), request.link(self.model), ''),
        )
