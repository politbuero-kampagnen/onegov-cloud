from onegov.activity import Invoice, InvoiceItem, Activity, \
    Occasion
from onegov.core.security import Secret
from onegov.feriennet import FeriennetApp, _
from onegov.feriennet.exports.base import FeriennetExport
from onegov.feriennet.forms import PeriodExportForm
from onegov.user import User
from sqlalchemy.orm import contains_eager
from sqlalchemy import distinct


@FeriennetApp.export(
    id='rechnungspositionen',
    form_class=PeriodExportForm,
    permission=Secret,
    title=_("Invoice Items"),
    explanation=_("Exports invoice items in the given period."),
)
class InvoiceItemExport(FeriennetExport):

    def run(self, form, session):
        return self.rows(session, form.selected_period)

    def rows(self, session, period):
        for item, tags in self.query(session, period):
            yield ((k, v) for k, v in self.fields(item, tags))

    def query(self, session, period):

        # There might be activities with same title from other periods
        # resulting in double entries of invoice items
        # We filter by the period in order to get the correct tags
        activities = session.query(
            distinct(Activity.title).label('title'),
            Activity._tags.label('tags')
        ).join(Occasion).filter(
            Occasion.period_id == period.id
        )
        activities = activities.subquery()

        q = session.query(InvoiceItem, activities.c.tags)
        q = q.join(Invoice).join(User)
        q = q.join(
            activities, InvoiceItem.text == activities.c.title, isouter=True
        )
        q = q.options(
            contains_eager(InvoiceItem.invoice)
            .contains_eager(Invoice.user)
            .undefer(User.data))
        q = q.filter(Invoice.period_id == period.id)
        q = q.order_by(
            User.username,
            InvoiceItem.group,
            InvoiceItem.text
        )
        return q

    def fields(self, item, tags):
        yield from self.invoice_item_fields(item)
        yield from self.user_fields(item.invoice.user)
        yield from self.activity_tags(tags)
