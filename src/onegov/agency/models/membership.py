from onegov.core.orm.mixins import meta_property
from onegov.org.models.extensions import AccessExtension
from onegov.people import AgencyMembership


class ExtendedAgencyMembership(AgencyMembership, AccessExtension):
    """ An extended version of the standard membership from onegov.people. """

    __mapper_args__ = {'polymorphic_identity': 'extended'}

    es_type_name = 'extended_membership'

    @property
    def es_public(self):
        if self.agency and self.agency.access != 'public':
            return False

        if self.person and self.person.access != 'public':
            return False

        return self.access == 'public'

    #: The prefix character.
    prefix = meta_property()

    #: A note to the membership.
    note = meta_property()

    #: An addition to the membership.
    addition = meta_property()
