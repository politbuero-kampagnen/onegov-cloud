from onegov.form import FormCollection
from onegov.reservation import ResourceCollection
from onegov.org.elements import Link, LinkGroup
from onegov.org.models import ImageSetCollection, PublicationCollection
from onegov.people import PersonCollection
from onegov.town import TownApp, _


@TownApp.homepage_widget(tag='services')
class ServicesWidget(object):
    template = """
        <xsl:template match="services">
            <h2 tal:content="services_panel.title"></h2>

            <metal:block use-macro="layout.macros['panel-links']"
                tal:define="panel services_panel"
            />
        </xsl:template>
    """

    def get_service_links(self, layout):
        yield Link(
            text=_("Online Counter"),
            url=layout.request.class_link(FormCollection),
            subtitle=(
                layout.org.meta.get('online_counter_label')
                or _("Forms and applications")
            )
        )

        # only if there are publications, will we enable the link to them
        if not layout.org.hide_publications and layout.app.publications_count:
            yield Link(
                text=_("Publications"),
                url=layout.request.class_link(PublicationCollection),
                subtitle=_(
                    layout.org.meta.get('publications_label')
                    or _("Official Documents")
                )
            )

        yield Link(
            text=_("Reservations"),
            url=layout.request.class_link(ResourceCollection),
            subtitle=(
                layout.org.meta.get('reservations_label')
                or _("Daypasses and rooms")
            )
        )

        if layout.org.meta.get('e_move_url'):
            yield Link(
                text=_("E-Move"),
                url=layout.org.meta.get('e_move_url'),
                subtitle=(
                    layout.org.meta.get('e_move_label')
                    or _("Move with eMovingCH")
                )
            )

        resources = ResourceCollection(layout.app.libres_context)

        # ga-tageskarte is the legacy name
        sbb_daypass = resources.by_name('sbb-tageskarte') \
            or resources.by_name('ga-tageskarte')

        if sbb_daypass:
            yield Link(
                text=_("SBB Daypass"),
                url=layout.request.link(sbb_daypass),
                subtitle=(
                    layout.org.meta.get('daypass_label')
                    or _("Generalabonnement for Towns")
                )
            )

    def get_variables(self, layout):
        return {
            'services_panel': LinkGroup(_("Services"), links=tuple(
                self.get_service_links(layout)
            ))
        }


@TownApp.homepage_widget(tag='contacts_and_albums')
class ContactsAndAlbumsWidget(object):

    template = """
        <xsl:template match="contacts_and_albums">
            <h3 tal:content="contacts_and_albums_panel.title"></h3>

            <metal:block use-macro="layout.macros['panel-links']"
                tal:define="panel contacts_and_albums_panel"
            />
        </xsl:template>
    """

    def get_variables(self, layout):
        request = layout.request

        return {
            'contacts_and_albums_panel': LinkGroup(
                title=_("Contacts and Photos"),
                links=[
                    Link(
                        text=_("People"),
                        url=request.class_link(PersonCollection),
                        subtitle=_("All contacts")
                    ),
                    Link(
                        text=_("Photo Albums"),
                        url=request.class_link(ImageSetCollection),
                        subtitle=_("Impressions")
                    ),
                ]
            )
        }
