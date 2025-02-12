from onegov.core.security import Secret
from onegov.feriennet import _
from onegov.feriennet.app import FeriennetApp
from onegov.feriennet.const import DEFAULT_DONATION_AMOUNTS
from onegov.feriennet.utils import format_donation_amounts
from onegov.feriennet.utils import parse_donation_amounts
from onegov.form import Form
from onegov.form.fields import MultiCheckboxField
from onegov.form.validators import Stdnum
from onegov.org.forms.fields import HtmlField
from onegov.org.models import Organisation
from onegov.org.views.settings import handle_generic_settings
from onegov.feriennet.qrbill import qr_iban
from onegov.feriennet.qrbill import swiss_iban
from onegov.feriennet.qrbill import beneficiary_to_creditor
from stdnum import iban
from wtforms.fields import BooleanField, StringField, RadioField, TextAreaField
from wtforms.fields.html5 import URLField
from wtforms.validators import InputRequired


class FeriennetSettingsForm(Form):

    bank_account = StringField(
        label=_("Bank Account (IBAN)"),
        fieldset=_("Payment"),
        validators=[Stdnum(format='iban')]
    )

    bank_beneficiary = StringField(
        label=_("Beneficiary"),
        fieldset=_("Payment"),
        description=_("Ferienpass Musterlingen, Bahnhofstr. 2, 1234 Beispiel"),
    )

    bank_reference_schema = RadioField(
        label=_("Payment Order"),
        fieldset=_("Payment"),
        choices=[
            ('feriennet-v1', _("Basic")),
            ('esr-v1', _("ESR (General)")),
            ('raiffeisen-v1', _("ESR (Raiffeisen)"))
        ],
        default='feriennet-v1'
    )

    bank_esr_participant_number = StringField(
        label=_("ESR participant number"),
        fieldset=_("Payment"),
        validators=[InputRequired()],
        depends_on=('bank_reference_schema', '!feriennet-v1')
    )

    bank_esr_identification_number = StringField(
        label=_("ESR identification number"),
        fieldset=_("Payment"),
        validators=[InputRequired()],
        depends_on=('bank_reference_schema', 'raiffeisen-v1')
    )

    bank_qr_bill = BooleanField(
        label=_("QR-Bill (experimental)"),
        fieldset=_("Payment")
    )

    require_full_age_for_registration = BooleanField(
        label=_("Full age required for registration"),
        fieldset=_("Userprofile"))

    show_political_municipality = BooleanField(
        label=_("Require the political municipality in the userprofile"),
        fieldset=_("Userprofile"))

    show_related_contacts = BooleanField(
        label=_(
            "Parents can see the contacts of other parents in "
            "the same activity"
        ),
        fieldset=_("Privacy")
    )

    public_organiser_data = MultiCheckboxField(
        label=_("Public organiser data"),
        choices=(
            ('name', _("Name")),
            ('address', _("Address")),
            ('email', _("E-Mail")),
            ('phone', _("Phone")),
            ('website', _("Website"))
        ),
        fieldset=_("Organiser")
    )

    tos_url = URLField(
        label=_("Link to the TOS"),
        description=_("Require users to accept the TOS before booking"),
        fieldset=_("TOS")
    )

    donation = BooleanField(
        label=_("Donations"),
        description=_("Show a donation button in the invoice view"),
        default=True,
        fieldset=_("Donation"))

    donation_amounts = TextAreaField(
        label=_("Donation Amounts"),
        description=_("One amount per line"),
        depends_on=('donation', 'y'),
        render_kw={'rows': 3},
        fieldset=_("Donation"))

    donation_description = HtmlField(
        label=_("Description"),
        depends_on=('donation', 'y'),
        fieldset=_("Donation"),
        render_kw={'rows': 10})

    volunteers = RadioField(
        label=_("Volunteer registration"),
        fieldset=_("Experimental"),
        choices=[
            ('disabled', _("Disabled")),
            ('admins', _("Only for Admins")),
            ('enabled', _("Enabled")),
        ],
        default='disabled'
    )

    def ensure_beneificary_if_bank_account(self):
        if self.bank_account.data and not self.bank_beneficiary.data:
            self.bank_beneficiary.errors.append(_(
                "A beneficiary is required if a bank account is given."
            ))
            return False

    def ensure_valid_esr_identification_number(self):
        if self.bank_reference_schema.data == 'raiffeisen-v1':
            ident = self.bank_esr_identification_number.data

            if not 3 <= len(ident.replace('-', ' ').strip()) <= 6:
                self.bank_esr_identification_number.errors.append(_(
                    "The ESR identification number must be 3-6 characters long"
                ))
                return False

    def ensure_valid_qr_bill_settings(self):
        if self.bank_qr_bill.data:
            if not self.bank_account.data:
                self.bank_qr_bill.errors.append(_("QR-Bills require an IBAN"))
                return False

            if not iban.is_valid(self.bank_account.data):
                self.bank_account.errors.append(_("Not a valid IBAN"))
                return False

            if not swiss_iban(self.bank_account.data):
                self.bank_account.errors.append(_(
                    "QR-Bills require a Swiss or Lichteinstein IBAN"
                ))
                return False

            if qr_iban(self.bank_account.data):
                if self.bank_reference_schema.data == 'feriennet-v1':
                    self.bank_account.errors.append(_(
                        "This IBAN cannot be used for QR-Bills without ESR"
                    ))
                    return False
            else:
                if self.bank_reference_schema.data != 'feriennet-v1':
                    self.bank_account.errors.append(_(
                        "This IBAN cannot be used for QR-Bills with ESR"
                    ))
                    return False

            if not self.bank_beneficiary.data:
                self.bank_qr_bill.errors.append(_(
                    "QR-Bills require a beneficiary"
                ))
                return False

            if not beneficiary_to_creditor(self.bank_beneficiary.data):
                self.bank_beneficiary.errors.append(_(
                    "QR-Bills require the beneficiary to be in the form: "
                    "name, street number, code city"
                ))
                return False

    def process_obj(self, obj):
        super().process_obj(obj)

        attributes = (
            ('show_political_municipality', False),
            ('require_full_age_for_registration', False),
            ('show_related_contacts', False),
            ('public_organiser_data', self.request.app.public_organiser_data),
            ('bank_account', ''),
            ('bank_beneficiary', ''),
            ('bank_reference_schema', 'feriennet-v1'),
            ('bank_esr_participant_number', ''),
            ('bank_esr_identification_number', ''),
            ('bank_qr_bill', False),
            ('tos_url', ''),
            ('donation', True),
            ('donation_amounts', DEFAULT_DONATION_AMOUNTS),
            ('donation_description', ''),
            ('volunteers', 'disabled'),
        )

        for attr, default in attributes:
            value = obj.meta.get(attr, default)

            if attr == 'donation_amounts':
                value = format_donation_amounts(value)

            getattr(self, attr).data = value

    def populate_obj(self, obj, *args, **kwargs):
        super().populate_obj(obj, *args, **kwargs)

        attributes = (
            'show_political_municipality',
            'require_full_age_for_registration',
            'show_related_contacts',
            'public_organiser_data',
            'bank_account',
            'bank_beneficiary',
            'bank_reference_schema',
            'bank_esr_participant_number',
            'bank_esr_identification_number',
            'bank_qr_bill',
            'tos_url',
            'donation',
            'donation_amounts',
            'donation_description',
            'volunteers',
        )

        for attr in attributes:
            value = getattr(self, attr).data

            if attr == 'donation_amounts':
                value = parse_donation_amounts(value)

            obj.meta[attr] = value


@FeriennetApp.form(model=Organisation, name='feriennet-settings',
                   template='form.pt', permission=Secret,
                   form=FeriennetSettingsForm, setting=_("Feriennet"),
                   icon='fa-child')
def custom_handle_settings(self, request, form):
    return handle_generic_settings(self, request, form, _("Feriennet"))
