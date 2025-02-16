import decimal
from collections import OrderedDict
from decimal import Decimal
from functools import partial
from onegov.core.security import Private
from onegov.form import merge_forms
from onegov.org import OrgApp, _
from onegov.org.forms import DateRangeForm, ExportForm
from onegov.org.layout import PaymentCollectionLayout, DefaultLayout
from onegov.org.mail import send_ticket_mail
from onegov.org.models import PaymentMessage, TicketMessage
from onegov.core.elements import Link
from sedate import align_range_to_day, standardize_date, as_datetime
from onegov.pay import Payment
from onegov.pay import PaymentCollection
from onegov.pay import PaymentProviderCollection
from onegov.ticket import TicketCollection
from webob import exc


EMAIL_SUBJECTS = {
    'marked-as-paid': _("Your payment has been received"),
    'marked-as-unpaid': _("Your payment has been withdrawn"),
    'refunded': _("Your payment has been refunded")
}


def ticket_by_link(tickets, link):
    if link.__tablename__ == 'reservations':
        return tickets.by_handler_id(link.token.hex)
    elif link.__tablename__ == 'submissions':
        return tickets.by_handler_id(link.id.hex)


def send_ticket_notifications(payment, request, change):
    session = request.session
    tickets = TicketCollection(session)

    for link in payment.links:
        ticket = ticket_by_link(tickets, link)

        if not ticket:
            continue

        # create a notification in the chat
        PaymentMessage.create(payment, ticket, request, change)

        if change == 'captured':
            continue

        # send an e-mail
        email = ticket.snapshot.get('email') or ticket.handler.email

        send_ticket_mail(
            request=request,
            template='mail_payment_change.pt',
            subject=EMAIL_SUBJECTS[change],
            receivers=(email, ),
            ticket=ticket,
            content={
                'model': ticket,
                'payment': payment,
                'change': change
            }
        )


@OrgApp.html(
    model=PaymentCollection,
    template='payments.pt',
    permission=Private)
def view_payments(self, request, layout=None):
    tickets = TicketCollection(request.session)

    providers = {
        provider.id: provider
        for provider in PaymentProviderCollection(request.session).query()
    }

    payment_links = self.payment_links_by_batch()

    return {
        'title': _("Payments"),
        'layout': layout or PaymentCollectionLayout(self, request),
        'payments': self.batch,
        'get_ticket': partial(ticket_by_link, tickets),
        'providers': providers,
        'payment_links': payment_links
    }


@OrgApp.form(
    model=PaymentCollection,
    name='export',
    template='form.pt',
    permission=Private,
    form=merge_forms(DateRangeForm, ExportForm))
def export_payments(self, request, form, layout=None):
    layout = layout or PaymentCollectionLayout(self, request)
    layout.breadcrumbs.append(Link(_("Export"), '#'))
    layout.editbar_links = None

    if form.submitted(request):
        start, end = align_range_to_day(
            standardize_date(as_datetime(form.data['start']), layout.timezone),
            standardize_date(as_datetime(form.data['end']), layout.timezone),
            layout.timezone)

        return form.as_export_response(
            run_export(
                session=request.session,
                start=start,
                end=end,
                nested=form.format == 'json',
                formatter=layout.export_formatter(form.format)
            )
        )

    return {
        'title': _("Export"),
        'layout': layout,
        'form': form
    }


def run_export(session, start, end, nested, formatter):
    collection = PaymentCollection(session, start=start, end=end)

    payments = tuple(collection.subset())
    links = collection.payment_links_by_batch(payments)

    def transform(payment, links):
        r = OrderedDict()
        r['source'] = payment.source
        r['source_id'] = payment.remote_id
        r['state'] = payment.state
        r['currency'] = payment.currency
        r['gross'] = payment.amount
        r['net'] = round(payment.net_amount, 2)
        r['fee'] = round(payment.fee, 2)
        r['payout_id'] = payment.meta.get('payout_id')
        r['payout_date'] = payment.meta.get('payout_date')

        if nested:
            r['references'] = [l.payable_reference for l in links]
        else:
            r['references'] = '\n'.join(l.payable_reference for l in links)

        for key in r:
            r[key] = formatter(r[key])

        return r

    return tuple(transform(p, links[p.id]) for p in payments)


@OrgApp.json(
    model=Payment,
    name='change-net-amount',
    request_method='POST',
    permission=Private
)
def change_payment_amount(self, request):
    request.assert_valid_csrf_token()
    assert not self.paid
    format_ = DefaultLayout(self, request).format_number
    try:
        net_amount = Decimal(request.params['netAmount'])
    except decimal.InvalidOperation:
        return {'net_amount': f"{format_(self.net_amount)} {self.currency}"}

    if net_amount <= 0 or (net_amount - self.fee) <= 0:
        raise exc.HTTPBadRequest("amount negative")

    links = self.links
    if links:
        tickets = TicketCollection(request.session)
        ticket = ticket_by_link(tickets, links[0])
        if ticket:
            TicketMessage.create(ticket, request, 'change-net-amount')

    self.amount = net_amount - self.fee
    return {'net_amount': f"{format_(self.net_amount)} {self.currency}"}


@OrgApp.view(
    model=Payment,
    name='mark-as-paid',
    request_method='POST',
    permission=Private)
def mark_as_paid(self, request):
    request.assert_valid_csrf_token()
    send_ticket_notifications(self, request, 'marked-as-paid')

    request.success(_("The ticket was marked as paid"))

    assert self.source == 'manual'
    self.state = 'paid'


@OrgApp.view(
    model=Payment,
    name='mark-as-unpaid',
    request_method='POST',
    permission=Private)
def mark_as_unpaid(self, request):
    request.assert_valid_csrf_token()
    send_ticket_notifications(self, request, 'marked-as-unpaid')

    request.success(_("The ticket was marked as unpaid"))

    assert self.source == 'manual'
    self.state = 'open'


@OrgApp.view(
    model=Payment,
    name='capture',
    request_method='POST',
    permission=Private)
def capture(self, request):
    request.assert_valid_csrf_token()
    send_ticket_notifications(self, request, 'captured')

    request.success(_("The payment was captured"))

    assert self.source == 'stripe_connect'
    self.charge.capture()


@OrgApp.view(
    model=Payment,
    name='refund',
    request_method='POST',
    permission=Private)
def refund(self, request):
    request.assert_valid_csrf_token()
    send_ticket_notifications(self, request, 'refunded')

    request.success(_("The payment was refunded"))

    assert self.source == 'stripe_connect'
    self.refund()
