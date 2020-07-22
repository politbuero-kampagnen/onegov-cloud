from onegov.core.utils import module_path
from onegov.org.theme import OrgTheme

NEWSGOT = '"NewsGot", Verdana, Arial, sans-serif;'

# options editable by the user
user_options = {
    'primary-color-ui': '#e33521',
    'body-font-family-ui': NEWSGOT,
    'header-font-family-ui': NEWSGOT
}


class WinterthurTheme(OrgTheme):
    name = 'onegov.winterthur.foundation'

    @property
    def post_imports(self):
        return super().post_imports + [
            'winterthur'
        ]

    @property
    def extra_search_paths(self):
        base_paths = super().extra_search_paths
        return [module_path('onegov.winterthur.theme', 'styles')] + base_paths

    @property
    def pre_imports(self):
        return super().pre_imports + [
            'winterthur-foundation-mods'
        ]
