import sedate

from datetime import datetime, time
from isodate import parse_date, parse_datetime
from lxml import etree
from lxml.html import fragments_fromstring
from onegov.town import _
from onegov.town.elements import DeleteLink, Link


def mark_images(html):
    """ Takes the given html and marks every paragraph with an 'has-img'
    class, if the paragraph contains an img element.

    """

    if not html:
        return html

    fragments = fragments_fromstring(html)

    # we perform a root xpath lookup, which will result in all paragraphs
    # being looked at - so we don't need to loop over all elements (yah, it's
    # a bit weird)
    for element in fragments[:1]:

        # instead of failing, lxml will return strings instead of elements if
        # they can't be parsed.. so we have to inspect the objects
        if not hasattr(element, 'xpath'):
            return html

        for paragraph in element.xpath('//p[img]'):
            if 'class' in paragraph.attrib:
                paragraph.attrib['class'] += ' has-img'
            else:
                paragraph.attrib['class'] = 'has-img'

    return ''.join(etree.tostring(e).decode('utf-8') for e in fragments)


def parse_fullcalendar_request(request, timezone):
    """ Parses start and end from the given fullcalendar request. It is
    expected that no timezone is passed (the default).

    See `<http://fullcalendar.io/docs/timezone/timezone/>`_

    :returns: A tuple of timezone-aware datetime objects or (None, None).

    """
    start = request.params.get('start')
    end = request.params.get('end')

    if start and end:
        if 'T' in start:
            start = parse_datetime(start)
            end = parse_datetime(end)
        else:
            start = datetime.combine(parse_date(start), time(0, 0))
            end = datetime.combine(parse_date(end), time(23, 59, 59, 999999))

        start = sedate.replace_timezone(start, timezone)
        end = sedate.replace_timezone(end, timezone)

        return start, end
    else:
        return None, None


class AllocationEventInfo(object):

    __slots__ = ['allocation', 'availability', 'request', 'translate']

    def __init__(self, allocation, request):
        self.allocation = allocation
        self.availability = allocation.availability
        self.request = request
        self.translate = request.translate

    @property
    def event_start(self):
        return self.allocation.display_start().isoformat()

    @property
    def event_end(self):
        return self.allocation.display_end().isoformat()

    @property
    def event_identification(self):
        return '{:%d.%m.%Y}: {}'.format(
            self.allocation.display_start(),
            self.event_time
        )

    @property
    def event_time(self):
        if self.allocation.whole_day:
            return self.translate(_("Whole day"))
        else:
            return '{:%H:%M} - {:%H:%M}'.format(
                self.allocation.display_start(),
                self.allocation.display_end()
            )

    @property
    def event_title(self):
        if self.allocation.partly_available:
            available = self.translate(_("${percent}% available", mapping={
                'percent': self.availability
            }))
        else:
            available = self.translate(_("${num}/${max} available", mapping={
                'num': self.allocation.quota,
                'max': self.allocation.quota_left
            }))

        return '\n'.join((self.event_time, available))

    @property
    def event_class(self):
        if self.availability >= 80.0:
            return 'event-available'
        if self.availability >= 20.0:
            return 'event-partly-available'
        else:
            return 'event-unavailable'

    @property
    def event_actions(self):
        yield Link(_("Reserve"), '#', classes=('new-reservation', ))

        if self.request.is_logged_in:
            yield Link(
                _("Edit"),
                self.request.link(self.allocation, name='bearbeiten'),
                classes=('edit-link', )
            )

            if self.availability == 100.0:
                yield DeleteLink(
                    _("Delete"),
                    self.request.link(self.allocation),
                    confirm=_("Do you really want to delete this allocation?"),
                    extra_information=self.event_identification,
                    yes_button_text=_("Delete allocation")
                )
            else:
                yield DeleteLink(
                    _("Delete"),
                    self.request.link(self.allocation),
                    confirm=_(
                        "This allocation can't be deleted because there are "
                        "existing reservations associated with it."
                    ),
                    extra_information=_(
                        "To delete this allocation, all existing reservations "
                        "need to be cancelled first."
                    )
                )

    def as_dict(self):
        return {
            'start': self.event_start,
            'end': self.event_end,
            'title': self.event_title,
            'className': self.event_class,
            'actions': [
                link(self.request).decode('utf-8')
                for link in self.event_actions
            ],
            'editurl': self.request.link(self.allocation, name='bearbeiten')
        }
