from morepath import redirect
from onegov.org import _
from onegov.org import OrgApp
from onegov.org.forms import ManageUserGroupForm
from onegov.org.layout import UserGroupCollectionLayout
from onegov.org.layout import UserGroupLayout
from onegov.core.elements import Link
from onegov.core.security import Secret
from onegov.user import UserGroup
from onegov.user import UserGroupCollection


def get_usergroup_form_class(model, request):
    return getattr(
        request.app.settings.org, 'usergroup_form_class', ManageUserGroupForm
    )


@OrgApp.html(
    model=UserGroupCollection,
    template='user_groups.pt',
    permission=Secret
)
def view_user_groups(self, request, layout=None):
    layout = layout or UserGroupCollectionLayout(self, request)

    return {
        'layout': layout,
        'title': _('User groups'),
        'groups': self.query().all()
    }


@OrgApp.form(
    model=UserGroupCollection,
    name='new',
    template='form.pt',
    permission=Secret,
    form=get_usergroup_form_class
)
def add_user_group(self, request, form, layout=None):
    if form.submitted(request):
        user_group = self.add(name=form.name.data)
        form.update_model(user_group)
        request.success(_('Added a new user group'))
        return redirect(request.link(user_group))

    layout = layout or UserGroupCollectionLayout(self, request)
    layout.breadcrumbs.append(Link(_('New user group'), '#'))

    return {
        'layout': layout,
        'title': _('New user group'),
        'form': form
    }


@OrgApp.html(
    model=UserGroup,
    template='user_group.pt',
    permission=Secret
)
def view_user_group(self, request, layout=None):
    layout = layout or UserGroupLayout(self, request)

    return {
        'layout': layout,
        'title': self.name,
    }


@OrgApp.form(
    model=UserGroup,
    name='edit',
    template='form.pt',
    permission=Secret,
    form=get_usergroup_form_class
)
def edit_user_group(self, request, form, layout=None):
    if form.submitted(request):
        form.update_model(self)
        request.success(_('Your changes were saved'))
        return redirect(request.link(self))

    if not form.errors:
        form.apply_model(self)

    layout = layout or UserGroupLayout(self, request)
    layout.breadcrumbs.append(Link(_('Edit user group'), '#'))

    return {
        'layout': layout,
        'title': _('Edit user group'),
        'form': form
    }


@OrgApp.view(
    model=UserGroup,
    request_method='DELETE',
    permission=Secret
)
def delete_user_group(self, request):
    request.assert_valid_csrf_token()
    UserGroupCollection(request.session).delete(self)
