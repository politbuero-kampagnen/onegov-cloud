import time

from abc import ABCMeta, abstractmethod
from uuid import uuid4

import morepath
from attr import attrs, attrib, validators
from sedate import utcnow

from onegov.core.crypto import random_token
from onegov.core.utils import rchop
from onegov.user import _, log, UserCollection, Auth
from onegov.user.auth.clients import KerberosClient
from onegov.user.auth.clients import LDAPClient
from onegov.user.auth.clients.msal import MSALConnections
from onegov.user.models.user import User
from translationstring import TranslationString
from typing import Dict
from typing import Optional
from webob import Response
from webob.exc import HTTPClientError


AUTHENTICATION_PROVIDERS = {}


def provider_by_name(providers, name):
    return next((p for p in providers if p.metadata.name == name), None)


class Conclusion(object):
    """ A final answer of :meth:`AuthenticationProvider`. """


@attrs(slots=True, frozen=True)
class Success(Conclusion):
    """ Indicates a sucessful authentication. """

    user: User = attrib()
    note: TranslationString = attrib()

    def __bool__(self):
        return True


@attrs(slots=True, frozen=True)
class Failure(Conclusion):
    """ Indicates a corrupt JWT """

    note: TranslationString = attrib()

    def __bool__(self):
        return False


class InvalidJWT(Failure):
    """ Indicates a failed authentication. """

    note: TranslationString = attrib()

    def __bool__(self):
        return False


@attrs(slots=True, frozen=True)
class ProviderMetadata(object):
    """ Holds provider-specific metadata. """

    name: str = attrib()
    title: str = attrib()


@attrs()
class AuthenticationProvider(metaclass=ABCMeta):
    """ Base class and registry for third party authentication providers. """

    # stores the 'to' attribute for the integration app
    # :class:`~onegov.user.integration.UserApp`.
    to: Optional[str] = attrib(init=False)

    @property
    def name(self):
        """ Needs to be available for the path in the integration app. """
        return self.metadata.name

    def __init_subclass__(cls, **kwargs):
        metadata = kwargs.pop('metadata', None)

        if metadata:
            global AUTHENTICATION_PROVIDERS
            assert metadata.name not in AUTHENTICATION_PROVIDERS

            # reserved names
            assert metadata.name not in ('auto', )

            cls.metadata = metadata
            AUTHENTICATION_PROVIDERS[metadata.name] = cls

        else:
            assert cls.kind in ('separate', 'integrated')

        super().__init_subclass__(**kwargs)

    @classmethod
    def configure(cls, **kwargs):
        """ This function gets called with the per-provider configuration
        defined in onegov.yml. Authentication providers may optionally
        access these values.

        The return value is either a provider instance, or none if the
        provider is not available.

        """

        return cls()

    def available(self, app):
        """Returns the the authentication provider is available for the current
        app. Since there are tenant specific connections, we might want to
        check, if for the tenant of the app, there is an available client."""
        return True


@attrs()
class SeparateAuthenticationProvider(AuthenticationProvider):
    """ Base class for separate authentication providers.

    Seperate providers render a button which the user can click to do a
    completely separate request/response handling that eventually should lead
    to an authenticated user.

    """

    kind = 'separate'

    @abstractmethod
    def authenticate_request(self, request):
        """ Authenticates the given request in one or many steps.

        Providers are expected to return one of the following values:

        * A conclusion (if the authentication was either successful or failed)
        * None (if the authentication failed)
        * A webob response (to perform handshakes)

        This function is called whenever the authentication is initiated by
        the user. If the provider returns a webob response, it is returned
        as is by the calling view.

        Therefore, `authenticate_request` must take care to return responses
        in a way that eventually end up fulfilling the authentication. At the
        very least, providers should ensure that all parameters of the original
        request are kept when asking external services to call back.

        """

    @abstractmethod
    def button_text(self, request):
        """ Returns the translatable button text for the given request.

        It is okay to return a static text, if the button remains the same
        for all requests.

        The translatable text is parsed as markdown, to add weight to
        the central element of the text. For example::

            Login with **Windows**

        """


@attrs()
class IntegratedAuthenticationProvider(AuthenticationProvider):
    """ Base class for integrated authentication providers.

    Integrated providers use the username/password entered in the normal
    login form and perform authentication that way (with fallback to the
    default login mechanism).

    """

    kind = 'integrated'

    @abstractmethod
    def hint(self, request):
        """ Returns the translatable hint shown above the login mask for
        the integrated provider.

        It is okay to return a static text, if the hint remains the same
        for all requests.

        The translatable text is parsed as markdown.

        """

    @abstractmethod
    def authenticate_user(self, request, username, password):
        """ Authenticates the given username/password in a single step.

        The function is expected to return an existing user record or None.

        """


def spawn_ldap_client(**cfg):
    """ Takes an LDAP configuration as found in the YAML and spawns an LDAP
    client that is connected. If the connection fails, an exception is raised.

    """
    client = LDAPClient(
        url=cfg.get('ldap_url', None),
        username=cfg.get('ldap_username', None),
        password=cfg.get('ldap_password', None))

    try:
        client.try_configuration()
    except Exception as e:
        raise ValueError(f"LDAP config error: {e}")

    return client


def ensure_user(source, source_id, session, username, role, force_role=True,
                realname=None, force_active=False):
    """ Creates the given user if it doesn't already exist. Ensures the
    role is set to the given role in all cases.
    """

    users = UserCollection(session)

    # find the user by source and
    if source and source_id:
        user = users.by_source_id(source, source_id)
    else:
        user = None

    # fall back to the username
    user = user or users.by_username(username)

    if not user:
        user = users.add(
            username=username,
            password=random_token(),
            role=role
        )
    elif force_active and not user.active:
        user.active = True

    # update the username
    user.username = username

    # update the role even if the user exists already
    if force_role:
        user.role = role

    # the source of the user is always the last provider that was used
    user.source = source
    user.source_id = source_id
    user.realname = realname

    return user


@attrs(auto_attribs=True)
class RolesMapping(object):
    """ Takes a role mapping and provides access to it.

    A role mapping maps a onegov-cloud role to an LDAP role. For example:

        admins -> ACC_OneGovCloud_User

    The mapping comes in multiple
    levels. For example:

       * "__default__"         Fallback for all applications
       * "onegov_org"          Namespace specific config
       * "onegov_org/govikon"  Application specific config

    Each level contains a group name for admins, editors and members.
    See onegov.yml.example for an illustrated example.

    """

    roles: Dict[str, Dict[str, str]]

    def app_specific(self, app):
        if app.application_id in self.roles:
            return self.roles[app.application_id]

        if app.namespace in self.roles:
            return self.roles[app.namespace]

        return self.roles.get('__default__')

    def match(self, roles, groups):
        """ Takes a role mapping (the fallback, namespace, or app specific one)
        and matches it against the given LDAP groups.

        Returns the matched group or None.

        """
        groups = {g.lower() for g in groups}

        if roles['admins'].lower() in groups:
            return 'admin'

        if roles['editors'].lower() in groups:
            return 'editor'

        if roles['members'].lower() in groups:
            return 'member'

        return None


@attrs(auto_attribs=True)
class LDAPAttributes(object):
    """ Holds the LDAP server-specific attributes. """

    # the name of the Distinguished Name (DN) attribute
    name: str

    # the name of the e-mails attribute (returns a list of emails)
    mails: str

    # the name of the group membership attribute (returns a list of groups)
    groups: str

    # the name of the password attribute
    password: str

    # the name of the uid attribute
    uid: str

    @classmethod
    def from_cfg(cls, cfg):
        return cls(
            name=cfg.get('name_attribute', 'cn'),
            mails=cfg.get('mails_attribute', 'mail'),
            groups=cfg.get('groups_attribute', 'memberOf'),
            password=cfg.get('password_attribute', 'userPassword'),
            uid=cfg.get('uid_attribute', 'uid'),
        )


@attrs(auto_attribs=True)
class LDAPProvider(
        IntegratedAuthenticationProvider, metadata=ProviderMetadata(
            name='ldap', title=_("LDAP"))):

    """ Generic LDAP Provider that includes authentication via LDAP. """

    # The LDAP client to use
    ldap: LDAPClient = attrib()

    # The authentication method to use
    #
    #   * bind =>    The authentication is made by rebinding the connection
    #                to the LDAP server. This is the more typical approach, but
    #                also slower. It requires that users that can authenticate
    #                may also create a connection to the LDAP server.
    #
    #                (not yet implemented)
    #
    #   * compare => Uses the existing LDAP client connection and checks the
    #                given password using the LDAP COMPARE operation. Since
    #                this is the first approach we implemented, it is the
    #                default.
    #
    auth_method: str = attrib(
        validator=validators.in_(
            ('bind', 'compare')
        )
    )

    # The LDAP attributes configuration
    attributes: LDAPAttributes = attrib()

    # Roles configuration
    roles: RolesMapping = attrib()

    # Custom hint to be shown in the login view
    custom_hint: str = ''

    @classmethod
    def configure(cls, **cfg):

        # Providers have to decide themselves if they spawn or not
        if not cfg:
            return None

        # LDAP configuration
        ldap = spawn_ldap_client(**cfg)

        return cls(
            ldap=ldap,
            auth_method=cfg.get('auth_method', 'compare'),
            attributes=LDAPAttributes.from_cfg(cfg),
            custom_hint=cfg.get('hint', None),
            roles=RolesMapping(cfg.get('roles', {
                '__default__': {
                    'admins': 'admins',
                    'editors': 'editors',
                    'members': 'members'
                }
            })),
        )

    def hint(self, request):
        return self.custom_hint

    def authenticate_user(self, request, username, password):
        if self.auth_method == 'compare':
            return self.authenticate_using_compare(request, username, password)

        raise NotImplementedError()

    def authenticate_using_compare(self, request, username, password):

        # since this is turned into an LDAP query, we want to make sure this
        # is not used to make broad queries
        assert '*' not in username
        assert '&' not in username
        assert '?' not in username

        # onegov-cloud uses the e-mail as username, therefore we need to query
        # LDAP to get the designated name (actual LDAP username)
        query = f"({self.attributes.mails}={username})"
        attrs = (
            self.attributes.groups,
            self.attributes.mails,
            self.attributes.uid
        )

        # we query the groups at the same time, so if we have a password
        # match we are all ready to go
        entries = self.ldap.search(query, attrs)

        # as a fall back, we try to query the uid
        if not entries:
            query = f"({self.attributes.uid}={username})"
            entries = self.ldap.search(query, attrs)

            # if successful we need the e-mail address
            for name, attrs in (entries or {}).items():
                try:
                    username = attrs[self.attributes.mails][0]
                except IndexError:
                    log.warning(
                        f'Email missing in LDAP for user with uid {username}')
                    return
                break

        # then, we give up
        if not entries:
            log.warning(f"No LDAP user with uid ore-mail {username}")
            return

        if len(entries) > 1:
            log.warning(f"Found more than one user for e-mail {username}")
            log.warning("All but the first user will be ignored")

        for name, attrs in entries.items():
            groups = attrs[self.attributes.groups]
            uid = attrs[self.attributes.uid][0]

            # do not iterate over all entries, or this becomes a very
            # handy way to check a single password against multiple
            # (or possibly all) entries!
            break

        # We might talk to a very fast LDAP server which an attacker could use
        # to brute force passwords. We already throttle this on the server, but
        # additional measures never hurt.
        time.sleep(0.25)

        if not self.ldap.compare(name, self.attributes.password, password):
            log.warning(f"Wrong password for {username} ({name})")
            return

        # finally check if we have a matching role
        role = self.roles.match(self.roles.app_specific(request.app), groups)

        if not role:
            log.warning(f"Wrong role for {username} ({name})")
            return

        return ensure_user(
            source=self.name,
            source_id=uid,
            session=request.session,
            username=username,
            role=role)


@attrs(auto_attribs=True)
class LDAPKerberosProvider(
        SeparateAuthenticationProvider, metadata=ProviderMetadata(
            name='ldap_kerberos', title=_("LDAP Kerberos"))):

    """ Combines LDAP with Kerberos. LDAP handles authorisation, Kerberos
    handles authentication.

    """

    # The LDAP client to use
    ldap: LDAPClient = attrib()

    # The Kerberos client to use
    kerberos: KerberosClient = attrib()

    # LDAP attributes configuration
    attributes: LDAPAttributes = attrib()

    # Roles configuration
    roles: RolesMapping = attrib()

    # Optional suffix that is removed from the Kerberos username if present
    suffix: Optional[str] = None

    @classmethod
    def configure(cls, **cfg):

        # Providers have to decide themselves if they spawn or not
        if not cfg:
            return None

        # LDAP configuration
        ldap = spawn_ldap_client(**cfg)

        # Kerberos configuration
        kerberos = KerberosClient(
            keytab=cfg.get('kerberos_keytab', None),
            hostname=cfg.get('kerberos_hostname', None),
            service=cfg.get('kerberos_service', None))

        return cls(
            ldap=ldap,
            kerberos=kerberos,
            attributes=LDAPAttributes.from_cfg(cfg),
            suffix=cfg.get('suffix', None),
            roles=RolesMapping(cfg.get('roles', {
                '__default__': {
                    'admins': 'admins',
                    'editors': 'editors',
                    'members': 'members'
                }
            }))
        )

    def button_text(self, request):
        """ Returns the request tailored to each OS (users won't understand
        LDAP/Kerberos, but for them it's basically their local OS login).

        """
        user_os = request.agent['os']['family']

        if user_os == "Other":
            return _("Login with operating system")

        return _("Login with **${operating_system}**", mapping={
            'operating_system': user_os
        })

    def authenticate_request(self, request):
        response = self.kerberos.authenticated_username(request)

        # handshake
        if isinstance(response, Response):
            return response

        # authentication failed
        if response is None or isinstance(response, HTTPClientError):
            return Failure(_("Authentication failed"))

        # we got authentication, do we also have authorization?
        name = response
        user = self.request_authorization(request=request, username=name)

        if user is None:
            return Failure(_("User «${user}» is not authorized", mapping={
                'user': name
            }))

        return Success(user, _("Successfully logged in as «${user}»", mapping={
            'user': user.username
        }))

    def request_authorization(self, request, username):

        if self.suffix:
            username = rchop(username, self.suffix)

        entries = self.ldap.search(
            query=f'({self.attributes.name}={username})',
            attributes=[self.attributes.mails, self.attributes.groups])

        if not entries:
            log.warning(f"No LDAP entries for {username}")
            return None

        if len(entries) > 1:
            tip = ', '.join(entries.keys())
            log.warning(f"Multiple LDAP entries for {username}: {tip}")
            return None

        attributes = next(v for v in entries.values())

        mails = attributes[self.attributes.mails]
        if not mails:
            log.warning(f"No e-mail addresses for {username}")
            return None

        groups = attributes[self.attributes.groups]
        if not groups:
            log.warning(f"No groups for {username}")
            return None

        # get the common name of the groups
        groups = {g.lower().split(',')[0].split('cn=')[-1] for g in groups}

        # get the roles
        roles = self.roles.app_specific(request.app)

        if not roles:
            log.warning(f"No role map for {request.app.application_id}")
            return None

        role = self.roles.match(roles, groups)
        if not role:
            log.warning(f"No authorized group for {username}")
            return None

        return ensure_user(
            source=self.name,
            source_id=username,
            session=request.session,
            username=mails[0],
            role=role)


@attrs
class OauthProvider(SeparateAuthenticationProvider):
    """General Prototype class for an Oath Provider with typical OAuth flow.
    """

    @abstractmethod
    def logout_url(self, request):
        """ Returns the tenant or app specific logout url to the authentication
        endpoint in a consistent manner.
         """

    @abstractmethod
    def request_authorisation(self, request):
        """
        Takes the request from the redirect_uri view sent from the users
        browser. The redirect view expects either:
        * a Conclusion, either Success or Failure
        * a webob response, e.g. to redirect to the logout page

        The redirect view, where this function is used, will eventually fulfill
        the login process whereas :func:`self.authenticate_request` is purely
        to redirect the user to the auth provider.
        """

    @staticmethod
    def logout_redirect_uri(request):
        """This url usually has to be registered with the OAuth Provider.
        Should not contain any query parameters. """
        return request.class_link(Auth, name='logout')

    def redirect_uri(self, request):
        """Returns the redirect uri in a consistent manner
        without query parameters."""
        return request.class_link(
            AuthenticationProvider,
            {'name': self.metadata.name},
            name='redirect'
        )


@attrs(auto_attribs=True)
class AzureADProvider(
    OauthProvider,
    metadata=ProviderMetadata(name='msal', title=_("AzureAD"))
):
    """
    Authenticates and authorizes a user in AzureAD for a specific AzureAD
    tenant_id and client_id in an OpenID Connect flow.

    For this to work, we need

        - Client ID
        - Client Secret
        - Tenant ID

    We have to give the AzureAD manager following Urls, that should not change:

        - Redirect uri (https://<host>/auth_providers/msal/redirect)
        - Logout Redirect uri (https://<host>/auth/logout)

    Additionally, weh AzureAD Manager should set additional token claims
    for the authorisation to work:

        - `email` claim
        - `groups` claim for role mapping
        - optional: `family_name` and `given_name` for User.realname

    The claims `preferred_username` or `upn` could also be used for
    User.realname."""

    # msal instances by tenant
    tenants: MSALConnections = attrib()

    # Roles configuration
    roles: RolesMapping = attrib()

    # Custom hint to be shown in the login view
    custom_hint: str = ''

    @classmethod
    def configure(cls, **cfg):

        if not cfg:
            return None

        return cls(
            tenants=MSALConnections.from_cfg(cfg.get('tenants')),
            custom_hint=cfg.get('hint', None),
            roles=RolesMapping(cfg.get('roles', {
                '__default__': {
                    'admins': 'admins',
                    'editors': 'editors',
                    'members': 'members'
                }
            }))
        )

    def button_text(self, request):
        return _("Login with Microsoft")

    def logout_url(self, request):
        client = self.tenants.client(request.app)
        return client.logout_url(self.logout_redirect_uri(request))

    def authenticate_request(self, request):
        """
        Returns a redirect response or a Conclusion

        Parameters of the original request are kept for when external services
        call back.
        """

        app = request.app
        client = self.tenants.client(app)
        roles = self.roles.app_specific(app)

        if not roles:
            # Considered as a misconfiguration of the app
            log.error(f"No role map for {app.application_id}")
            return Failure(_('Authorisation failed due to an error'))

        if not client:
            # Considered as a misconfiguration of the app
            log.error(f'No msal client found for '
                      f'{app.application_id} or {app.namespace}')
            return Failure(_('Authorisation failed due to an error'))

        state = app.sign(str(uuid4()))
        nonce = str(uuid4())
        request.browser_session['state'] = state
        request.browser_session['login_to'] = self.to
        request.browser_session['nonce'] = nonce

        # We can not include self.to, the redirect uri must always be the same
        auth_url = client.connection.get_authorization_request_url(
            scopes=[],
            state=state,
            redirect_uri=self.redirect_uri(request),
            response_type='code',
            nonce=nonce
        )

        return morepath.redirect(auth_url)

    def validate_id_token(self, request, token):
        """
        Makes sure the id token is validated correctly according to
        https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation
        """

        app = request.app
        client = self.tenants.client(app)
        id_token_claims = token.get('id_token_claims', {})
        iss = id_token_claims.get('iss')

        endpoint = client.connection.authority.token_endpoint
        endpoint = endpoint.replace('oauth2/', '').replace('token', '')
        endpoint = endpoint.rstrip('/')

        if iss != endpoint:
            log.info(f'Issue claim check failed: {iss} v.s {endpoint}')
            return Failure(_('Authorisation failed due to an error'))

        now = utcnow().timestamp()
        iat = id_token_claims.get('iat')
        if iat > now:
            log.info(f'IAT check failed: {iat} > {now}')
            return Failure(_('Authorisation failed due to an error'))
        exp = id_token_claims.get('exp')
        if now > exp:
            log.info(f'EXP check failed, token expired: {now} > {exp}')
            return Failure(_('Your login has expired'))

        return True

    def request_authorisation(self, request):
        """
        If "Stay Logged In" on the Microsoft Login page is chosen,
        AzureAD behaves like an auto-login provider, redirecting the user back
        immediately to the redirect view without prompting a password or
        even showing any Microsoft page. Microsoft set their own cookies to
        make this possible.

        Return a webob Response or a Conclusion.
        """
        # Fetch the state that was saved upon first redirect
        app = request.app
        state = request.browser_session.get('state')

        client = self.tenants.client(app)
        roles = self.roles.app_specific(app)

        if request.params.get('state') != state:
            log.warning('state is not matching, csrf check failed')
            return Failure(_('Authorisation failed due to an error'))

        authorization_code = request.params.get('code')

        if authorization_code is None:
            log.warning('No code found in url query params')
            return Failure(_('Authorisation failed due to an error'))

        # Must take the same redirect url as used in the first step
        # The nonce is evaluated inside msal library and raises ValueError
        token_result = client.connection.acquire_token_by_authorization_code(
            authorization_code,
            scopes=[],
            redirect_uri=self.redirect_uri(request),
            nonce=request.browser_session.pop('nonce')
        )

        if "error" in token_result:
            log.info(
                f"Error in token result - "
                f"{token_result['error']}: "
                f"{token_result.get('error_description')}"
            )
            return Failure(_('Authorisation failed due to an error'))

        validate_conclusion = self.validate_id_token(request, token_result)
        if not validate_conclusion:
            return validate_conclusion

        id_token_claims = token_result.get('id_token_claims', {})
        username = id_token_claims.get(client.attributes.username)
        source_id = id_token_claims.get(client.attributes.source_id)
        groups = id_token_claims.get(client.attributes.groups)
        first_name = id_token_claims.get(client.attributes.first_name)
        last_name = id_token_claims.get(client.attributes.last_name)
        preferred_username = id_token_claims.get(
            client.attributes.preferred_username)

        if not username:
            log.info("No username found in authorisation step")
            return Failure(_('Authorisation failed due to an error'))

        if not source_id:
            log.info(f"No source_id found for {username}")
            return Failure(_('Authorisation failed due to an error'))

        if not groups:
            log.info(f"No groups found for {username}")
            return Failure(_("Can't login because your user has no groups. "
                             "Contact your AzureAD system administrator"))

        role = self.roles.match(roles, groups)

        if not role:
            log.info(f"No authorized group for {username}, "
                     f"having groups: {', '.join(groups)}")
            return Failure(_('Authorisation failed due to an error'))

        if first_name and last_name:
            realname = f'{first_name} {last_name}'
        else:
            realname = preferred_username

        user = ensure_user(
            source=self.name,
            source_id=source_id,
            session=request.session,
            username=username,
            role=role,
            realname=realname
        )

        # We set the path we wanted to go when starting the oauth flow
        self.to = request.browser_session.pop('login_to', '/')

        return Success(user, _("Successfully logged in as «${user}»", mapping={
            'user': user.username
        }))

    def available(self, app):
        return self.tenants.client(app) and True or False
