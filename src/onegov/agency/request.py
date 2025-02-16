from cached_property import cached_property
from onegov.org.request import OrgRequest


class AgencyRequest(OrgRequest):

    @cached_property
    def current_role(self):
        """ Onegov Agency allows to additionally elevate the member role to the
        editor role by defining group role mappings.

        """
        from onegov.agency.security import get_current_role
        return get_current_role(self.session, self.identity)
