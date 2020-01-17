from onegov.feriennet import _
from cached_property import cached_property
from onegov.activity import Activity, Occasion
from onegov.feriennet import FeriennetApp
from onegov.feriennet.layout import DefaultLayout
from onegov.org.models import Boardlet, BoardletFact


class FeriennetBoardlet(Boardlet):

    @cached_property
    def session(self):
        return self.request.session

    @cached_property
    def period(self):
        return self.request.app.active_period

    @cached_property
    def layout(self):
        return DefaultLayout(None, self.request)

    @property
    def group_title(self):
        return self.period and self.period.title or _("No active period")


@FeriennetApp.boardlet(name='period', order=(1, 1))
class PeriodBoardlet(FeriennetBoardlet):

    @property
    def title(self):
        return self.period and self.period.title or _("No active period")

    @property
    def facts(self):
        if not self.period:
            return

        def icon(checked):
            return checked and 'fa-check-square-o' or 'fa-square-o'

        yield BoardletFact(
            text=_("Prebooking: ${dates}", mapping={
                'dates': self.layout.format_date_range(
                    self.period.prebooking_start,
                    self.period.prebooking_end,
                )
            }),
            icon=icon(self.period.confirmed)
        )

        yield BoardletFact(
            text=_("Booking: ${dates}", mapping={
                'dates': self.layout.format_date_range(
                    self.period.booking_start,
                    self.period.booking_end,
                )
            }),
            icon=icon(self.period.finalized)
        )

        yield BoardletFact(
            text=_("Execution: ${dates}", mapping={
                'dates': self.layout.format_date_range(
                    self.period.execution_start,
                    self.period.execution_end,
                )
            }),
            icon=icon(self.period.is_execution_in_past)
        )


@FeriennetApp.boardlet(name='activities', order=(1, 2))
class ActivitiesBoardlet(FeriennetBoardlet):

    @cached_property
    def occasions_count(self):
        if not self.period:
            return 0

        return self.session.query(Occasion)\
            .filter_by(period_id=self.period.id)\
            .count()

    @cached_property
    def activities_count(self):
        if not self.period:
            return 0

        return self.session.query(Activity).filter(Activity.id.in_(
            self.session.query(Occasion.activity_id)
                .filter_by(period_id=self.period.id)
                .subquery()
        )).count()

    @property
    def title(self):
        return _("${count} Activities", mapping={
            'count': self.activities_count
        })

    @property
    def facts(self):
        if not self.period:
            return

        yield BoardletFact(
            text=_("${count} Activities", mapping={
                'count': self.activities_count
            }),
            icon='fa-dot-circle-o'
        )

        yield BoardletFact(
            text=_("${count} Occasions", mapping={
                'count': self.occasions_count
            }),
            icon='fa-circle-o'
        )
