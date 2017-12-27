import requests
import stripe
import transaction

from cached_property import cached_property
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from html import escape
from onegov.core.orm.mixins import meta_property
from onegov.pay import log
from onegov.pay.models.payment import Payment
from onegov.pay.models.payment_provider import PaymentProvider
from onegov.pay.utils import Price
from sqlalchemy.orm import object_session
from uuid import UUID, uuid4, uuid5


@contextmanager
def stripe_api_key(key):
    old_key = stripe.api_key
    stripe.api_key = key
    yield
    stripe.api_key = old_key


# instantiate once to get keep-alive support
stripe.default_http_client = stripe.http_client.RequestsClient()


# our stripe payment ids are generated by using the token and a UUID namespace
STRIPE_NAMESPACE = UUID('aebb1a32-282b-4521-838d-92a1136624d1')


class StripeCaptureManager(object):
    """ Captures an open stripe charge when the transaction finishes.

    If there is an error during this step, it is logged, but the transaction
    still continues successfully.

    The user is then supposed to manually capture the charge.

    """

    transaction_manager = transaction.manager

    def __init__(self, api_key, charge_id):
        self.api_key = api_key
        self.charge_id = charge_id

    @classmethod
    def capture_charge(cls, api_key, charge_id):
        transaction.get().join(cls(api_key, charge_id))

    def sortKey(self):
        return 'charge'

    def tpc_vote(self, transaction):
        with stripe_api_key(self.api_key):
            self.charge = stripe.Charge.retrieve(self.charge_id)

    def tpc_finish(self, transaction):
        try:
            with stripe_api_key(self.api_key):
                self.charge.capture()
        except Exception as e:
            # we can never fail or we might end up with an incosistent
            # database -> so must swallow any errors and report them
            log.exception("Stripe charge with capture id {} failed".format(
                self.charge_id
            ))

    def commit(self, transaction):
        pass

    def abort(self, transaction):
        pass

    def tpc_begin(self, transaction):
        pass

    def tpc_abort(self, transaction):
        pass


class StripeFeePolicy(object):
    """ All stripe fee calculations in one place (should they ever change). """

    percentage = 0.029
    fixed = 0.3

    @classmethod
    def from_amount(cls, amount):
        """ Gets the fee for the given amount. """

        return round(float(amount) * cls.percentage + cls.fixed, 2)

    @classmethod
    def compensate(cls, amount):
        """ Increases the amount in such a way that the stripe fee is included
        in the effective charge (that is, the user paying the charge is paying
        the fee as well).

        """

        return round((float(amount) + cls.fixed) / (1 - cls.percentage), 2)


class StripePayment(Payment):
    __mapper_args__ = {'polymorphic_identity': 'stripe_connect'}

    fee_policy = StripeFeePolicy

    #: the date of the payout
    payout_date = meta_property('payout_date')

    #: the id of the payout
    payout_id = meta_property('payout_id')

    #: the fee deducted by stripe
    effective_fee = meta_property('effective_fee')

    @property
    def fee(self):
        """ The calculated fee or the effective fee if available.

        The effective fee is taken from the payout records. In practice
        these values should always be the same.

        """

        if self.effective_fee:
            return Decimal(self.effective_fee)

        return Decimal(self.fee_policy.from_amount(self.amount))

    @property
    def remote_url(self):
        if self.provider.livemode:
            base = 'https://dashboard.stripe.com/payments/{}'
        else:
            base = 'https://dashboard.stripe.com/test/payments/{}'

        return base.format(self.remote_id)

    @property
    def charge(self):
        with stripe_api_key(self.provider.access_token):
            return stripe.Charge.retrieve(self.remote_id)

    def refund(self):
        with stripe_api_key(self.provider.access_token):
            refund = stripe.Refund.create(charge=self.remote_id)
            self.state = 'cancelled'
            return refund

    def sync(self, remote_obj=None):
        charge = remote_obj or self.charge

        if not charge.captured:
            self.state = 'open'

        elif charge.refunded:
            self.state = 'cancelled'

        elif charge.status == 'failed':
            self.state = 'failed'

        elif charge.captured and charge.paid:
            self.state = 'paid'


class StripeConnect(PaymentProvider):

    __mapper_args__ = {'polymorphic_identity': 'stripe_connect'}

    fee_policy = StripeFeePolicy

    #: The Stripe Connect client id
    client_id = meta_property('client_id')

    #: The API key of the connect user
    client_secret = meta_property('client_secret')

    #: The oauth_redirect gateway in use (see seantis/oauth_redirect on github)
    oauth_gateway = meta_property('oauth_gateway')

    #: The auth code required by oauth_redirect
    oauth_gateway_auth = meta_property('oauth_gateway_auth')

    #: The oauth_redirect secret that should be used
    oauth_gateway_secret = meta_property('oauth_gateway_secret')

    #: The authorization code provided by OAuth
    authorization_code = meta_property('authorization_code')

    #: The public stripe key
    publishable_key = meta_property('publishable_key')

    #: The stripe user id as confirmed by OAuth
    user_id = meta_property('user_id')

    #: The refresh token provided by OAuth
    refresh_token = meta_property('refresh_token')

    #: The access token provieded by OAuth
    access_token = meta_property('access_token')

    #: The id of the latest processed balance transaction
    latest_payout = meta_property('latest_payout')

    #: Should the fee be charged to the customer or not?
    charge_fee_to_customer = meta_property('charge_fee_to_customer')

    def adjust_price(self, price):
        if self.charge_fee_to_customer:
            new_price = self.fee_policy.compensate(price.amount)
            new_fee = self.fee_policy.from_amount(new_price)

            return Price(new_price, price.currency, new_fee)

        return price

    @property
    def livemode(self):
        return not self.access_token.startswith('sk_test')

    @property
    def payment_class(self):
        return StripePayment

    @property
    def title(self):
        return 'Stripe Connect'

    @property
    def url(self):
        return 'https://dashboard.stripe.com/'

    @property
    def public_identity(self):
        account = self.account
        return ' / '.join((account.business_name, account.email))

    @property
    def identity(self):
        return self.user_id

    @cached_property
    def account(self):
        with stripe_api_key(self.access_token):
            return stripe.Account.retrieve(id=self.user_id)

    @property
    def connected(self):
        return self.account and True or False

    def charge(self, amount, currency, token):
        session = object_session(self)

        payment = self.payment(
            id=uuid5(STRIPE_NAMESPACE, token),
            amount=amount,
            currency=currency,
            state='open'
        )

        with stripe_api_key(self.access_token):
            charge = stripe.Charge.create(
                amount=round(amount * 100, 0),
                currency=currency,
                source=token,
                capture=False,
                idempotency_key=token,
                metadata={
                    'payment_id': payment.id.hex
                }
            )

        StripeCaptureManager.capture_charge(self.access_token, charge.id)
        payment.remote_id = charge.id

        # we do *not* want to lose this information, so even though the
        # caller should make sure the payment is stored, we make sure
        session.add(payment)

        return payment

    def checkout_button(self, label, amount, currency, action='submit',
                        **extra):
        """ Generates the html for the checkout button. """

        extra['amount'] = round(amount * 100, 0)
        extra['currency'] = currency
        extra['key'] = self.publishable_key

        attrs = {
            'data-stripe-{}'.format(key): str(value)
            for key, value in extra.items()
        }
        attrs['data-action'] = action

        return """
            <input type="hidden" name="payment_token" id="{target}">
            <button class="checkout-button stripe-connect"
                    data-target-id="{target}"
                    {attrs}>{label}</button>
        """.format(
            label=escape(label),
            attrs=' '.join(
                '{}="{}"'.format(escape(k), escape(v))
                for k, v in attrs.items()
            ),
            target=uuid4().hex
        )

    def oauth_url(self, redirect_uri, state=None, user_fields=None):
        """ Generates an oauth url to be shown in the browser. """

        return stripe.OAuth.authorize_url(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope='read_write',
            redirect_uri=redirect_uri,
            stripe_user=user_fields,
            state=state
        )

    def prepare_oauth_request(self, redirect_uri, success_url, error_url,
                              user_fields=None):
        """ Registers the oauth request with the oauth_gateway and returns
        an url that is ready to be used for the complete oauth request.

        """
        register = '{}/register/{}'.format(
            self.oauth_gateway,
            self.oauth_gateway_auth)

        assert self.oauth_gateway \
            and self.oauth_gateway_auth \
            and self.oauth_gateway_secret

        payload = {
            'url': redirect_uri,
            'secret': self.oauth_gateway_secret,
            'method': 'GET',
            'success_url': success_url,
            'error_url': error_url
        }

        response = requests.post(register, json=payload)
        assert response.status_code == 200

        return self.oauth_url(
            redirect_uri='{}/redirect'.format(self.oauth_gateway),
            state=response.json()['token'],
            user_fields=user_fields
        )

    def process_oauth_response(self, request_params):
        """ Takes the parameters of an incoming oauth request and stores
        them on the payment provider if successful.

        """

        if 'error' in request_params:
            raise RuntimeError("Stripe OAuth request failed ({}: {})".format(
                request_params['error'], request_params['error_description']
            ))

        assert request_params['oauth_redirect_secret'] \
            == self.oauth_gateway_secret

        self.authorization_code = request_params['code']

        with stripe_api_key(self.client_secret):
            token = stripe.OAuth.token(
                grant_type='authorization_code',
                code=self.authorization_code,
            )

        assert token.data['scope'] == 'read_write'

        self.publishable_key = token.data['stripe_publishable_key']
        self.user_id = token.data['stripe_user_id']
        self.refresh_token = token.data['refresh_token']
        self.access_token = token.data['access_token']

    def sync(self):
        session = object_session(self)
        self.sync_payment_states(session)
        self.sync_payouts(session)

    def sync_payment_states(self, session):

        def payments(ids):
            q = session.query(self.payment_class)
            q = q.filter(self.payment_class.id.in_(ids))

            return q

        charges = self.paged(
            stripe.Charge.list,
            limit=50,
            include=lambda r: 'payment_id' in r.metadata
        )

        by_payment = {}

        for charge in charges:
            by_payment[charge.metadata['payment_id']] = charge

        for payment in payments(by_payment.keys()):
            payment.sync(remote_obj=by_payment[payment.id.hex])

    def sync_payouts(self, session):

        payouts = self.paged(stripe.Payout.list, limit=50, status='paid')
        latest_payout = None

        paid_charges = {}

        for payout in payouts:
            if latest_payout is None:
                latest_payout = payout

            if payout.id == self.latest_payout:
                break

            transactions = self.paged(
                stripe.BalanceTransaction.list,
                limit=50,
                payout=payout.id,
                type='charge'
            )

            for charge in transactions:
                paid_charges[charge.source] = (
                    datetime.fromtimestamp(payout.arrival_date),
                    payout.id,
                    charge.fee / 100
                )

        if paid_charges:
            q = session.query(self.payment_class)
            q = q.filter(self.payment_class.remote_id.in_(paid_charges.keys()))

            for p in q:
                p.payout_date, p.payout_id, p.effective_fee\
                    = paid_charges[p.remote_id]

        self.latest_payout = latest_payout and latest_payout.id

    def paged(self, method, include=lambda record: True, **kwargs):
        with stripe_api_key(self.access_token):
            records = method(**kwargs)
            records = (r for r in records.auto_paging_iter())
            records = (r for r in records if include(r))

            yield from records
