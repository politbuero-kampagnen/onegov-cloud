from decimal import Decimal
from onegov.activity import Period, Invoice, InvoiceItem, InvoiceCollection, \
    PeriodCollection
from onegov.core.security import Personal, Secret
from onegov.core.templates import render_macro
from onegov.feriennet import FeriennetApp, _
from onegov.feriennet.collections import BillingCollection
from onegov.feriennet.forms import DonationForm
from onegov.feriennet.layout import DonationLayout
from onegov.feriennet.layout import InvoiceLayout
from onegov.feriennet.qrbill import generate_qr_bill
from onegov.feriennet.views.shared import users_for_select_element
from onegov.pay import process_payment, INSUFFICIENT_FUNDS
from onegov.user import User
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import case
from stdnum import iban


@FeriennetApp.view(
    model=InvoiceItem,
    permission=Personal,
)
def redirect_to_invoice_view(self, request):
    return request.redirect(
        request.link(
            InvoiceCollection(
                request.session,
                user_id=self.invoice.user_id,
                period_id=self.invoice.period_id
            )
        )
    )


@FeriennetApp.view(
    model=InvoiceItem,
    permission=Secret,
    name='online-payments'
)
def view_creditcard_payments(self, request):
    return request.redirect(request.class_link(
        BillingCollection,
        {
            'username': self.invoice.user.username,
            'period_id': self.invoice.period_id
        }, name='online-payments'
    ))


@FeriennetApp.html(
    model=InvoiceCollection,
    template='invoices.pt',
    permission=Personal)
def view_my_invoices(self, request):
    query = PeriodCollection(request.session).query()
    query = query.filter(Period.finalized == True)
    periods = {p.id.hex: p for p in query}

    # By default, we want to see all the invoices, unless a specific one
    # is selected. This is a bit of a code-smell, because we usually would
    # want to set that through the model in the path directive.
    show_all_invoices = 'invoice' not in request.params

    q = self.query(ignore_period_id=show_all_invoices is True)
    q = q.filter(Invoice.period_id.in_(periods.keys()))
    q = q.outerjoin(Period)
    q = q.outerjoin(InvoiceItem)
    q = q.options(contains_eager(Invoice.items))
    q = q.order_by(
        Period.execution_start,
        Invoice.id,
        case(
            [
                (InvoiceItem.group == 'donation', 2),
                (InvoiceItem.family != None, 1),
            ],
            else_=0
        ),
        InvoiceItem.group,
        InvoiceItem.text
    )

    invoices = tuple(q)

    users = users_for_select_element(request)
    user = request.session.query(User).filter_by(id=self.user_id).first()

    if request.current_user.id == self.user_id:
        title = _("Invoices")
    else:
        title = _("Invoices of ${user}", mapping={
            'user': user.title
        })

    # make sure the invoice is set up with the latest configured reference,
    # which may result in a new reference record being added - this is done
    # ad-hoc on an invoice to invoice basis since we do not need a new
    # reference for an invoice that is never looked at
    for invoice in invoices:
        if not invoice.paid:
            self.schema.link(request.session, invoice)

    if self.schema.name == 'feriennet-v1':
        account = request.app.org.meta.get('bank_account')
        account = account and iban.format(account)
    else:
        account = request.app.org.meta.get('bank_esr_participant_number')

    beneficiary = request.app.org.meta.get('bank_beneficiary')
    payment_provider = request.app.default_payment_provider
    qr_bill_enabled = request.app.org.meta.get('bank_qr_bill', False)
    layout = InvoiceLayout(self, request, title)

    def payment_button(title, price):
        price = payment_provider.adjust_price(price)

        label = ': '.join((
            request.translate(_("Pay Online Now")),
            render_macro(layout.macros['price'], layout.request, {
                'layout': layout,
                'price': price,
                'show_fee': True
            })
        ))

        return request.app.checkout_button(
            button_label=label,
            title=title,
            price=price,
            email=user.username,
            locale=request.locale
        )

    def user_select_link(user):
        return request.class_link(InvoiceCollection, {
            'username': user.username,
        })

    def qr_bill(invoice):
        return generate_qr_bill(self.schema.name, request, user, invoice)

    return {
        'title': title,
        'layout': layout,
        'users': users,
        'user': user,
        'user_select_link': user_select_link,
        'invoices': invoices,
        'model': self,
        'account': account,
        'payment_provider': payment_provider,
        'payment_button': payment_button,
        'beneficiary': beneficiary,
        'invoice_bucket': request.app.invoice_bucket(),
        'qr_bill': qr_bill if qr_bill_enabled else None,
    }


@FeriennetApp.view(
    model=InvoiceCollection,
    template='invoices.pt',
    permission=Personal,
    request_method='POST')
def handle_payment(self, request):
    provider = request.app.default_payment_provider
    token = request.params.get('payment_token')
    period = request.params.get('period')

    invoice = self.for_period_id(period_id=period).query()\
        .outerjoin(InvoiceItem)\
        .one()

    price = request.app.default_payment_provider.adjust_price(invoice.price)
    payment = process_payment('cc', price, provider, token)

    if payment == INSUFFICIENT_FUNDS:
        request.alert(_("Your card has insufficient funds"))
    elif payment is None:
        request.alert(_("Your payment could not be processed"))
    else:
        for item in invoice.items:

            if item.paid:
                continue

            item.payments.append(payment)
            item.source = provider.type
            item.paid = True

        request.success(_("Your payment has been received. Thank you!"))

    return request.redirect(request.link(self))


@FeriennetApp.form(
    model=InvoiceCollection,
    form=DonationForm,
    template='donation.pt',
    permission=Personal,
    name='donation')
def handle_donation(self, request, form):
    if not self.user_id:
        return request.redirect(request.link(
            self.for_user_id(request.current_user.id),
            name='donation'
        ))

    if not self.period_id:
        return request.redirect(request.link(
            self.for_period_id(request.app.active_period.id),
            name='donation'
        ))

    if request.current_user.id == self.user_id:
        title = _("Donation")
    else:
        user = request.session.query(User).filter_by(id=self.user_id).first()
        title = _("Donation of ${user}", mapping={'user': user.title})

    period = request.app.periods_by_id[self.period_id.hex]
    bills = BillingCollection(request, period)

    if form.submitted(request):

        try:
            bills.include_donation(
                user_id=self.user_id,
                amount=Decimal(form.amount.data),
                text=request.translate(_("Donation")))
        except NoResultFound:
            request.alert(_("No invoice found"))
        else:
            request.success(_("Thank you for your donation"))
            return request.redirect(request.link(self))

    elif not request.POST:

        donation = \
            request.session.query(InvoiceItem)\
            .filter(InvoiceItem.group == 'donation')\
            .filter(
                InvoiceItem.invoice_id.in_(
                    request.session.query(Invoice.id)
                    .filter(Invoice.period_id == self.period_id)
                    .filter(Invoice.user_id == self.user_id)
                )
            ).first()

        if donation:
            amount = f'{donation.amount:.2f}'

            for key, value in form.amount.choices:
                if key == amount:
                    form.amount.data = amount
                    break

    description = request.app.org.meta.get('donation_description', '').strip()

    return {
        'title': title,
        'layout': DonationLayout(self, request, title),
        'form': form,
        'button_text': _("Donate"),
        'description': description,
    }


@FeriennetApp.view(
    model=InvoiceCollection,
    permission=Personal,
    name='donation',
    request_method='DELETE')
def handle_delete_donation(self, request):
    assert self.user_id and self.period_id
    request.assert_valid_csrf_token()

    period = request.app.periods_by_id[self.period_id.hex]
    bills = BillingCollection(request, period)

    if bills.exclude_donation(self.user_id):
        request.success(_("Your donation was removed"))
    else:
        request.alert(_("This donation has already been paid"))
