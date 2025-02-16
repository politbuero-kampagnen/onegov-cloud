""" The authentication views. """

import morepath

from onegov.core.markdown import render_untrusted_markdown
from onegov.core.security import Public, Personal
from onegov.org import _, OrgApp
from onegov.org import log
from onegov.org.elements import Link
from onegov.org.layout import DefaultLayout
from onegov.org.mail import send_transactional_html_mail
from onegov.user import Auth, UserCollection
from onegov.user.auth.provider import OauthProvider
from onegov.user.errors import AlreadyActivatedError
from onegov.user.errors import ExistingUserError
from onegov.user.errors import ExpiredSignupLinkError
from onegov.user.errors import InvalidActivationTokenError
from onegov.user.errors import UnknownUserError
from onegov.user.forms import LoginForm
from onegov.user.forms import PasswordResetForm
from onegov.user.forms import RegistrationForm
from onegov.user.forms import RequestPasswordResetForm
from purl import URL
from webob import exc


@OrgApp.form(model=Auth, name='login', template='login.pt', permission=Public,
             form=LoginForm)
def handle_login(self, request, form, layout=None):
    """ Handles the login requests. """

    if not request.app.enable_yubikey:
        form.delete_field('yubikey')

    if self.skippable(request):
        return self.redirect(request, self.to)

    if form.submitted(request):

        redirected_to_userprofile = False

        org_settings = request.app.settings.org
        if org_settings.require_complete_userprofile:
            username = form.username.data

            if not org_settings.is_complete_userprofile(request, username):
                redirected_to_userprofile = True

                self.to = request.return_to(
                    '/userprofile',
                    self.to
                )

        response = self.login_to(request=request, **form.login_data)

        if response:
            if redirected_to_userprofile:
                request.warning(_(
                    "Your userprofile is incomplete. "
                    "Please update it before you continue."
                ))
            else:
                request.success(_("You have been logged in."))

            return response

        request.alert(_("Wrong e-mail address, password or yubikey."))

    layout = layout or DefaultLayout(self, request)
    request.include('scroll-to-username')
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Login"), request.link(self, name='login'))
    ]

    def provider_login(provider):
        provider.to = self.to
        return request.link(provider)

    return {
        'layout': layout,
        'password_reset_link': request.link(self, name='request-password'),
        'register_link': request.link(self, name='register'),
        'may_register': request.app.enable_user_registration,
        'button_text': _("Login"),
        'providers': request.app.providers,
        'provider_login': provider_login,
        'render_untrusted_markdown': render_untrusted_markdown,
        'title': _('Login to ${org}', mapping={
            'org': request.app.org.title
        }),
        'form': form
    }


@OrgApp.form(model=Auth, name='register', template='form.pt',
             permission=Public, form=RegistrationForm)
def handle_registration(self, request, form, layout=None):
    """ Handles the user registration. """

    if not request.app.enable_user_registration:
        raise exc.HTTPNotFound()

    if form.submitted(request):

        try:
            user = self.register(form, request)
        except ExistingUserError:
            request.alert(_("A user with this address already exists"))
        except ExpiredSignupLinkError:
            request.alert(_("This signup link has expired"))
        else:
            url = URL(request.link(self, 'activate'))
            url = url.query_param('username', form.username.data)
            url = url.query_param('token', user.data['activation_token'])

            subject = request.translate(
                _("Your ${org} Registration", mapping={
                    'org': request.app.org.title
                })
            )

            send_transactional_html_mail(
                request=request,
                template='mail_activation.pt',
                subject=subject,
                receivers=(form.username.data, ),
                content={
                    'activation_link': url.as_string(),
                    'model': self
                }
            )
            request.success(_(
                "Thank you for registering. Please follow the instructions "
                "on the activiation e-mail sent to you."
            ))

            return morepath.redirect(request.link(request.app.org))

    layout = layout or DefaultLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Register"), request.link(self, name='register'))
    ]
    request.include('scroll-to-username')

    return {
        'layout': layout,
        'title': _('Account Registration'),
        'form': form
    }


@OrgApp.view(model=Auth, name='activate', permission=Public)
def handle_activation(self, request):

    if not request.app.enable_user_registration:
        raise exc.HTTPNotFound()

    users = UserCollection(request.session)

    username = request.params.get('username')
    token = request.params.get('token')

    try:
        users.activate_with_token(username, token)
    except UnknownUserError:
        request.warning(_("Unknown user"))
    except InvalidActivationTokenError:
        request.warning(_("Invalid activation token"))
    except AlreadyActivatedError:
        request.success(_("Your account has already been activated."))
    else:
        request.success(_(
            "Your account has been activated. "
            "You may now log in with your credentials"
        ))

    return morepath.redirect(request.link(request.app.org))


def do_logout(self, request, to=None):
    # the message has to be set after the log out code has run, since that
    # clears all existing messages from the session
    @request.after
    def show_hint(response):
        request.success(_("You have been logged out."))

    return self.logout_to(request, to)


def do_logout_with_external_provider(self, request):
    """ Use this function if you want to go the way to the external auth
    provider first and then logout on redirect. """
    from onegov.user.integration import UserApp  # circular import

    user = request.current_user
    if not user:
        do_logout(self, request)

    if isinstance(self.app, UserApp) and user.source:
        for provider in self.app.providers:
            if isinstance(provider, OauthProvider):
                if request.url == provider.logout_redirect_uri(request):
                    return do_logout(
                        self,
                        request,
                        to=request.browser_session.pop('logout_to', '/')
                    )
                request.browser_session['logout_to'] = self.to
                return morepath.redirect(provider.logout_url(request))


@OrgApp.html(model=Auth, name='logout', permission=Personal)
def view_logout(self, request):
    """ Handles the logout requests. We do not logout over external auth
    providers, since we anyway have like a hybrid login (using id_token to
    establish our own login session with different expiration). """
    return do_logout(self, request)


@OrgApp.form(model=Auth, name='request-password', template='form.pt',
             permission=Public, form=RequestPasswordResetForm)
def handle_password_reset_request(self, request, form, layout=None):
    """ Handles the GET and POST password reset requests. """

    if request.app.disable_password_reset:
        raise exc.HTTPNotFound()

    layout = layout or DefaultLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Reset password"), request.link(self, name='request-password'))
    ]

    if form.submitted(request):

        user = UserCollection(request.session)\
            .by_username(form.email.data)

        url = layout.password_reset_url(user)

        if url:
            send_transactional_html_mail(
                request=request,
                template='mail_password_reset.pt',
                subject=_("Password reset"),
                receivers=(user.username, ),
                content={'model': None, 'url': url}
            )
        else:
            log.info(
                "Failed password reset attempt by {}".format(
                    request.client_addr
                )
            )

        response = morepath.redirect(request.link(self, name='login'))
        request.success(
            _(('A password reset link has been sent to ${email}, provided an '
               'account exists for this email address.'),
              mapping={'email': form.email.data})
        )
        return response

    return {
        'layout': layout,
        'title': _('Reset password'),
        'form': form,
        'form_width': 'small'
    }


@OrgApp.form(model=Auth, name='reset-password', template='form.pt',
             permission=Public, form=PasswordResetForm)
def handle_password_reset(self, request, form, layout=None):

    if request.app.disable_password_reset:
        raise exc.HTTPNotFound()

    if form.submitted(request):
        # do NOT log the user in at this point - only onegov.user.auth does
        # logins - we only ever want one path to be able to login, which makes
        # it easier to do it correctly.

        if form.update_password(request):
            request.success(_("Password changed."))
            return morepath.redirect(request.link(self, name='login'))
        else:
            request.alert(
                _("Wrong username or password reset link not valid any more.")
            )
            log.info(
                "Failed password reset attempt by {}".format(
                    request.client_addr
                )
            )

    if 'token' in request.params:
        form.token.data = request.params['token']

    layout = layout or DefaultLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Reset password"), request.link(self, name='request-password'))
    ]

    return {
        'layout': layout,
        'title': _('Reset password'),
        'form': form,
        'form_width': 'small'
    }
