from base64 import b64decode
from gzip import GzipFile
from io import BytesIO

from lxml.etree import LxmlError

from onegov.activity import Invoice, InvoiceItem, InvoiceCollection
from onegov.activity.iso20022 import match_iso_20022_to_usernames
from onegov.core.custom import json
from onegov.core.elements import Link, Confirm, Intercooler, Block
from onegov.core.security import Secret
from onegov.feriennet import FeriennetApp, _
from onegov.feriennet.collections import BillingCollection
from onegov.feriennet.forms import BankStatementImportForm
from onegov.feriennet.forms import BillingForm
from onegov.feriennet.forms import ManualBookingForm
from onegov.feriennet.layout import BillingCollectionImportLayout
from onegov.feriennet.layout import BillingCollectionLayout
from onegov.feriennet.layout import BillingCollectionManualBookingLayout
from onegov.feriennet.layout import OnlinePaymentsLayout
from onegov.feriennet.models import InvoiceAction, PeriodMessage
from onegov.pay import Payment
from onegov.pay import PaymentProviderCollection
from onegov.pay import payments_association_table_for
from onegov.user import UserCollection, User
from purl import URL
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from urllib.parse import quote_plus


@FeriennetApp.form(
    model=BillingCollection,
    form=BillingForm,
    template='billing.pt',
    permission=Secret)
def view_billing(self, request, form):
    layout = BillingCollectionLayout(self, request)
    session = request.app.session

    if form.submitted(request) and not self.period.finalized:
        self.create_invoices(
            all_inclusive_booking_text=request.translate(_("Passport")))

        if form.finalize_period:
            PeriodMessage.create(self.period, request, 'finalized')
            self.period.finalized = True

    # we can generate many links here, so we need this to be
    # as quick as possible, which is why we only use one token
    csrf_token = request.new_csrf_token().decode('utf-8')

    filters = {
        'state': [
            Link(
                text=_("Paid"),
                active=self.state == 'paid',
                url=request.link(self.for_state('paid')),
                rounded=True,
            ),
            Link(
                text=_("Unpaid"),
                active=self.state == 'unpaid',
                url=request.link(self.for_state('unpaid')),
                rounded=True,
            ),
        ]
    }

    def csrf_protected(url):
        return URL(url).query_param('csrf-token', csrf_token).as_string()

    def as_link(action, traits):
        traits = (
            *(traits or tuple()),
            Intercooler(request_method='POST')
        )

        return Link(
            action.text,
            attrs={'class': action.action},
            url=csrf_protected(request.link(action)),
            traits=traits
        )

    def manual_booking_link(username):
        url = request.link(self, name='booking')
        url = f'{url}&for-user={quote_plus(username)}'

        return Link(
            _("Add manual booking"),
            attrs={'class': 'new-booking'},
            url=url
        )

    def invoice_links(details):
        if not self.period.finalized:
            return

        yield Link(
            _("Show invoice"),
            attrs={'class': 'show-invoice'},
            url=request.class_link(
                InvoiceCollection, {
                    'username': details.first.username,
                    'invoice': self.period.id.hex
                }
            )
        )

        if details.has_online_payments:
            yield Link(
                _("Show online payments"),
                attrs={'class': 'show-online-payments'},
                url=request.class_link(
                    InvoiceItem, {'id': details.first.id},
                    name='online-payments'
                )
            )

        yield manual_booking_link(details.first.username)

        if details.disable_changes:
            traits = (
                Block(_(
                    "This bill or parts of it have been paid online. "
                    "To change the state of the bill the payment "
                    "needs to be charged back."
                ), no=_("Cancel")),
            )

        elif details.discourage_changes:
            traits = (
                Confirm(
                    _(
                        "This bill or parts of it have been confirmed by "
                        "the bank, do you really want to change the "
                        "payment status?"
                    ),
                    None,
                    _("Yes"),
                    _("Cancel")
                ),
            )
        else:
            traits = None

        yield from (as_link(a, traits) for a in invoice_actions(details))

    def item_links(item):
        if not self.period.finalized:
            return

        if item.changes == 'impossible':
            traits = (
                Block(_(
                    "This position has been paid online. To change "
                    "the state of the position the payment needs to "
                    "be charged back."
                ), no=_("Cancel")),
            )

        elif item.changes == 'discouraged':
            traits = (
                Confirm(
                    _(
                        "This position has been confirmed by the bank, do "
                        "you really want to change the payment status?"
                    ),
                    None,
                    _("Yes"),
                    _("Cancel")
                ),
            )
        else:
            traits = None

        yield from (as_link(a, traits) for a in item_actions(item))

    def invoice_actions(details):
        if details.paid:
            yield InvoiceAction(
                session=session,
                id=details.first.id,
                action='mark-unpaid',
                extend_to='invoice',
                text=_("Mark whole bill as unpaid")
            )
        else:
            yield InvoiceAction(
                session=session,
                id=details.first.id,
                action='mark-paid',
                extend_to='invoice',
                text=_("Mark whole bill as paid")
            )

    def item_actions(item):
        if item.paid:
            yield InvoiceAction(
                session=session,
                id=item.id,
                action='mark-unpaid',
                text=_("Mark as unpaid")
            )
        else:
            yield InvoiceAction(
                session=session,
                id=item.id,
                action='mark-paid',
                text=_("Mark as paid")
            )

        if item.family:
            yield InvoiceAction(
                session=session,
                id=item.id,
                action='remove-manual',
                text=_("Remove manual booking")
            )

    return {
        'layout': layout,
        'title': _("Billing for ${title}", mapping={
            'title': self.period.title
        }),
        'model': self,
        'period': self.period,
        'periods': request.app.periods,
        'form': form,
        'button_text': _("Create Bills"),
        'invoice_links': invoice_links,
        'item_links': item_links,
        'filters': filters,
    }


@FeriennetApp.view(
    model=BillingCollection,
    name='reset',
    permission=Secret,
    request_method="POST")
def reset_billing(self, request):
    if not self.period.active:
        request.warning(
            _("The period must be active in order to reset billing"))
        return request.redirect(request.link(self))

    session = request.session

    for invoice in self.invoices.query():
        session.delete(invoice)

    request.success(_("The billing was successfully reset."))


@FeriennetApp.html(
    model=BillingCollection,
    permission=Secret,
    name='online-payments',
    template='online-payments.pt')
def view_online_payments(self, request):
    table = payments_association_table_for(InvoiceItem)
    session = request.session

    invoice_item_ids = self.invoices.query_items()
    invoice_item_ids = invoice_item_ids.with_entities(InvoiceItem.id)

    payment_ids = session.query(table.c.payment_id)
    payment_ids = payment_ids.filter(
        table.c.invoice_items_id.in_(invoice_item_ids.subquery()))

    payments = session.query(Payment).filter(
        Payment.id.in_(payment_ids.subquery()))

    payments = payments.order_by(desc(Payment.created))

    providers = {
        provider.id: provider
        for provider in PaymentProviderCollection(session).query()
    }

    title = _("Online Payments by ${name}", mapping={
        'name': request.app.user_titles_by_name[self.username]
    })

    layout = OnlinePaymentsLayout(self, request, title=title)

    def payment_actions(payment):
        if payment.state == 'paid':
            amount = '{:02f} {}'.format(payment.amount, payment.currency)

            yield Link(
                text=_("Refund Payment"),
                url=layout.csrf_protected_url(
                    request.link(payment, 'refund')
                ),
                attrs={'class': 'payment-refund'},
                traits=(
                    Confirm(
                        _("Do you really want to refund ${amount}?", mapping={
                            'amount': amount
                        }),
                        _("This cannot be undone."),
                        _("Refund ${amount}", mapping={
                            'amount': amount
                        }),
                        _("Cancel")
                    ),
                    Intercooler(
                        request_method='POST',
                        redirect_after=request.url
                    )
                )
            )

    return {
        'title': title,
        'payments': payments,
        'payment_actions': payment_actions,
        'providers': providers,
        'layout': layout,
    }


@FeriennetApp.view(
    model=InvoiceAction,
    permission=Secret,
    request_method='POST')
def execute_invoice_action(self, request):
    request.assert_valid_csrf_token()
    self.execute()

    @request.after
    def trigger_bill_update(response):
        if self.extend_to == 'family':
            response.headers.add('X-IC-Redirect', request.class_link(
                BillingCollection
            ))
        else:
            response.headers.add('X-IC-Trigger', 'reload-from')
            response.headers.add('X-IC-Trigger-Data', json.dumps({
                'selector': f'#{self.item.invoice_id}'
            }))


@FeriennetApp.view(
    model=BillingCollection,
    request_method='POST',
    name='execute-import',
    permission=Secret)
def view_execute_import(self, request):
    request.assert_valid_csrf_token()
    cache = request.browser_session.get('account-statement')
    if not cache:
        request.alert(_("Could not import payments. Check your import data."))
        return

    binary = BytesIO(b64decode(cache['data']))
    xml = GzipFile(filename='', mode='r', fileobj=binary).read()
    xml = xml.decode('utf-8')

    invoice = cache['invoice']

    transactions = list(
        match_iso_20022_to_usernames(xml, request.session, period_id=invoice))

    users = dict(
        request.session.query(User).with_entities(User.username, User.id))

    payments = {
        users[t.username]: t for t in transactions if t.state == 'success'}

    if payments:
        invoices = request.app.invoice_collection(period_id=invoice)
        invoices = invoices.query()
        invoices = invoices.filter(Invoice.user_id.in_(payments.keys()))

        for invoice in invoices.options(joinedload(Invoice.items)):
            for item in invoice.items:
                item.tid = payments[invoice.user_id].tid
                item.source = 'xml'
                item.paid = True

        request.success(_("Imported ${count} payments", mapping={
            'count': len(payments)
        }))
    else:
        request.alert(_("No payments could be imported"))

    del request.browser_session['account-statement']

    @request.after
    def redirect_intercooler(response):
        response.headers.add('X-IC-Redirect', request.link(self))


@FeriennetApp.form(
    model=BillingCollection,
    form=BankStatementImportForm,
    permission=Secret,
    name='import',
    template='billing_import.pt',
)
def view_billing_import(self, request, form):
    uploaded = 'account-statement' in request.browser_session

    if form.submitted(request):
        request.browser_session['account-statement'] = {
            'invoice': form.period.data,
            'data': form.xml.data['data']
        }
        uploaded = True
    elif not request.POST and uploaded:
        del request.browser_session['account-statement']
        uploaded = False

    if uploaded:
        cache = request.browser_session['account-statement']

        binary = BytesIO(b64decode(cache['data']))
        xml = GzipFile(filename='', mode='r', fileobj=binary).read()
        try:
            xml = xml.decode('utf-8')
        except UnicodeDecodeError:
            request.alert(_("The submitted xml data could not be decoded"))
            return request.redirect(request.link(self))

        try:
            transactions = list(
                match_iso_20022_to_usernames(
                    xml, request.session, period_id=cache['invoice']))
        except LxmlError:
            request.alert(_('The submitted xml data could not be parsed. '
                            'Please check the file integrity'))
            return request.redirect(request.link(self))

        if not transactions:
            del request.browser_session['account-statement']
            request.alert(_("No transactions were found in the given file"))
            uploaded = False
            form.xml.data = None
        else:
            transactions.sort(key=lambda t: t.order)
    else:
        transactions = None

    users = UserCollection(request.session)
    users = {
        u.username: (u.realname or u.username)
        for u in users.query().with_entities(User.username, User.realname)
    }

    layout = BillingCollectionImportLayout(self, request)

    return {
        'layout': layout,
        'title': _("Import Bank Statement"),
        'form': form if not uploaded else None,
        'button_text': _("Preview"),
        'transactions': transactions,
        'uploaded': uploaded,
        'users': users,
        'user_link': lambda u: request.class_link(
            InvoiceCollection, {'username': u}
        ),
        'success_count': transactions and sum(
            1 for t in transactions if t.state == 'success'
        ),
        'model': self,
        'post_url': layout.csrf_protected_url(
            request.link(self, 'execute-import')
        )
    }


@FeriennetApp.form(
    model=BillingCollection,
    form=ManualBookingForm,
    permission=Secret,
    name='booking',
    template='form.pt'
)
def view_manual_booking_form(self, request, form):
    if form.submitted(request):
        count = self.add_manual_position(form.users, form.text, form.amount)

        if not count:
            request.alert(_("No manual bookings were created."))
        else:
            request.success(_("Created ${count} manual bookings", mapping={
                'count': count
            }))

        return request.redirect(request.link(self))

    return {
        'layout': BillingCollectionManualBookingLayout(self, request),
        'title': _("Add manual booking"),
        'form': form
    }
