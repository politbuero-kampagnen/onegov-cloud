from cached_property import cached_property
from colour import Color
from onegov.core.utils import safe_format_keys
from onegov.directory import DirectoryConfiguration
from onegov.directory import DirectoryZipArchive
from onegov.form import as_internal_id
from onegov.form import flatten_fieldsets
from onegov.form import Form
from onegov.form import merge_forms
from onegov.form import move_fields
from onegov.form import parse_formcode
from onegov.form.errors import FormError
from onegov.form.fields import IconField, MultiCheckboxField
from onegov.form.fields import UploadField
from onegov.form.filters import as_float
from onegov.form.validators import FileSizeLimit
from onegov.form.validators import ValidFormDefinition
from onegov.form.validators import WhitelistedMimeType
from onegov.org import _
from onegov.org.forms.fields import HtmlField
from onegov.org.forms.generic import PaymentMethodForm
from onegov.org.theme.org_theme import user_options
from sqlalchemy.orm import object_session
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import RadioField
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import ValidationError
from wtforms import validators
from wtforms_components import ColorField


class DirectoryBaseForm(Form):
    """ Form for directories. """

    title = StringField(
        label=_("Title"),
        fieldset=_("General"),
        validators=[validators.InputRequired()])

    lead = TextAreaField(
        label=_("Lead"),
        fieldset=_("General"),
        description=_("Describes what this directory is about"),
        render_kw={'rows': 4})

    text = HtmlField(
        label=_("Further Information"),
        fieldset=_("General"))

    structure = TextAreaField(
        label=_("Definition"),
        fieldset=_("General"),
        validators=[
            validators.InputRequired(),
            ValidFormDefinition(
                require_email_field=False,
                require_title_fields=True
            )
        ],
        render_kw={'rows': 32, 'data-editor': 'form'})

    enable_map = RadioField(
        label=_("Coordinates"),
        fieldset=_("General"),
        choices=[
            (
                'no',
                _("Entries have no coordinates")
            ),
            (
                'entry',
                _("Coordinates are shown on each entry")
            ),
            (
                'everywhere',
                _("Coordinates are shown on the directory and on each entry")
            ),
        ],
        default='everywhere')

    title_format = StringField(
        label=_("Title-Format"),
        fieldset=_("Display"),
        validators=[validators.InputRequired()],
        render_kw={'class_': 'formcode-format'})

    lead_format = StringField(
        label=_("Lead-Format"),
        fieldset=_("Display"),
        render_kw={'class_': 'formcode-format'})

    content_fields = TextAreaField(
        label=_("Main view"),
        fieldset=_("Display"),
        render_kw={'class_': 'formcode-select'})

    content_hide_labels = TextAreaField(
        label=_("Hide these labels on the main view"),
        fieldset=_("Display"),
        render_kw={'class_': 'formcode-select'})

    contact_fields = TextAreaField(
        label=_("Address"),
        fieldset=_("Display"),
        render_kw={
            'class_': 'formcode-select',
            'data-fields-exclude': 'fileinput,radio,checkbox'
        })

    keyword_fields = TextAreaField(
        label=_("Filters"),
        fieldset=_("Display"),
        render_kw={
            'class_': 'formcode-select',
            'data-fields-include': 'radio,checkbox'
        })

    thumbnail = TextAreaField(
        label=_("Thumbnail"),
        fieldset=_("Display"),
        render_kw={
            'class_': 'formcode-select',
            'data-fields-include': 'fileinput'
        })

    show_as_thumbnails = TextAreaField(
        label=_("Pictures to be displayed as thumbnails on an entry"),
        fieldset=_("Display"),
        render_kw={
            'class_': 'formcode-select',
            'data-fields-include': 'fileinput'
        })

    address_block_title_type = RadioField(
        label=_("Address Block Title"),
        fieldset=_("Address Block"),
        default='auto',
        choices=(
            ('auto', _("The first line of the address")),
            ('fixed', _("Static title")),
        )
    )

    address_block_title = StringField(
        label=_("Title"),
        fieldset=_("Address Block"),
        depends_on=('address_block_title_type', 'fixed'),
    )

    marker_icon = IconField(
        label=_("Icon"),
        fieldset=_("Marker"))

    marker_color_type = RadioField(
        label=_("Marker Color"),
        fieldset=_("Marker"),
        choices=[
            ('default', _("Default")),
            ('custom', _("Custom"))
        ],
        default='default')

    marker_color_value = ColorField(
        label=_("Color"),
        fieldset=_("Marker"),
        depends_on=('marker_color_type', 'custom'))

    order = RadioField(
        label=_("Order"),
        fieldset=_("Order"),
        choices=[
            ('by-title', _("By title")),
            ('by-format', _("By format"))
        ],
        default='by-title')

    order_format = StringField(
        label=_("Order-Format"),
        fieldset=_("Order"),
        render_kw={'class_': 'formcode-format'},
        validators=[validators.InputRequired()],
        depends_on=('order', 'by-format'))

    order_direction = RadioField(
        label=_("Direction"),
        fieldset=_("Order"),
        choices=[
            ('asc', _("Ascending")),
            ('desc', _("Descending"))
        ],
        default='asc')

    link_pattern = StringField(
        label=_("Pattern"),
        fieldset=_("External Link"),
        render_kw={'class_': 'formcode-format'})

    link_title = StringField(
        label=_("Title"),
        fieldset=_("External Link"))

    link_visible = BooleanField(
        label=_("Visible"),
        fieldset=_("External Link"),
        default=True)

    enable_submissions = BooleanField(
        label=_("Users may propose new entries"),
        fieldset=_("New entries"),
        default=False)

    submissions_guideline = HtmlField(
        label=_("Guideline"),
        fieldset=_("New entries"),
        depends_on=('enable_submissions', 'y'))

    price = RadioField(
        label=_("Price"),
        fieldset=_("New entries"),
        choices=[
            ('free', _("Free of charge")),
            ('paid', _("Paid"))
        ],
        default='free',
        depends_on=('enable_submissions', 'y'))

    price_per_submission = DecimalField(
        label=_("Price per submission"),
        fieldset=_("New entries"),
        filters=(as_float, ),
        validators=[validators.Optional()],
        depends_on=('enable_submissions', 'y', 'price', 'paid'))

    currency = StringField(
        label=_("Currency"),
        fieldset=_("New entries"),
        default="CHF",
        depends_on=('enable_submissions', 'y', 'price', 'paid'),
        validators=[validators.InputRequired()])

    enable_change_requests = BooleanField(
        label=_("Users may send change requests"),
        fieldset=_("Change requests"),
        default=False)

    change_requests_guideline = HtmlField(
        label=_("Guideline"),
        fieldset=_("Change requests"),
        depends_on=('enable_change_requests', 'y'))

    enable_publication = BooleanField(
        label=_("Enable publication dates"),
        description=_("Users may suggest publication start and/or end "
                      "of the entry on submissions and change requests"),
        fieldset=_("Publication"),
        default=False)

    submitter_meta_fields = MultiCheckboxField(
        label=_("Information to be provided in addition to the E-mail"),
        choices=(
            ('submitter_name', _("Name")),
            ('submitter_address', _("Address")),
            ('submitter_phone', _("Phone")),
        ),
        fieldset=_("Submitter")
    )

    @cached_property
    def known_field_ids(self):
        try:
            return {
                field.id for field in
                flatten_fieldsets(parse_formcode(self.structure.data))
            }
        except FormError:
            return None

    @cached_property
    def missing_fields(self):
        try:
            return self.configuration.missing_fields(self.structure.data)
        except FormError:
            return None

    def extract_field_ids(self, field):
        if not self.known_field_ids:
            return

        for line in field.data.splitlines():
            line = line.strip()

            if as_internal_id(line) in self.known_field_ids:
                yield line

    def validate_title_format(self, field):
        if self.missing_fields and 'title' in self.missing_fields:
            raise ValidationError(
                _("The following fields are unknown: ${fields}", mapping={
                    'fields': ', '.join(self.missing_fields['title'])
                }))

    def validate_lead_format(self, field):
        if self.missing_fields and 'lead' in self.missing_fields:
            raise ValidationError(
                _("The following fields are unknown: ${fields}", mapping={
                    'fields': ', '.join(self.missing_fields['lead'])
                }))

    def validate_thumbnail(self, field):
        if field.data and '\n' in field.data:
            raise ValidationError(
                _("Please select at most one thumbnail field")
            )

    def ensure_public_fields_for_submissions(self):
        """ Force directories to show all fields (no hidden fields) if the
        user may send in new entries or update exsting ones.

        Otherwise we would have to filter out private fields which presents
        all kinds of edge-cases that we should probably not solve - directories
        are not meant to be private repositories.

        """
        inputs = (
            self.enable_change_requests,
            self.enable_submissions
        )

        if not any((i.data for i in inputs)):
            return

        hidden = self.first_hidden_field(self.configuration)

        if hidden:
            msg = _(
                "User submissions are not possible, because «${field}» "
                "is not visible. Only if all fields are visible are user "
                "submission possible - otherwise users may see data that "
                "they are not intended to see. ", mapping={
                    'field': hidden.label
                }
            )

            for i in inputs:
                if i.data:
                    i.errors.append(msg)

            return False

    def first_hidden_field(self, configuration):
        """ Returns the first hidden field, or None. """

        for field in flatten_fieldsets(parse_formcode(self.structure.data)):
            if not self.is_public(field.id, configuration):
                return field

    def is_public(self, fid, configuration):
        """ Returns true if the given field id is public.

        A field is public, if none of these are true:

            * It is part of the title/lead
            * It is part of the display
            * It is part of the keywords
            * It is used as the thumbnail

        Though we might also glean other fields if they are simply searchable
        or if they are part of the link pattern, we do not count those as
        public, because we are interested in *obviously* public fields
        clearly visible to the user.

        """

        # the display sets are not really defined at one single point…
        sets = ('contact', 'content')
        conf = configuration.display or {}

        for s in sets:
            if s not in conf:
                continue

            if fid in (as_internal_id(v) for v in conf[s]):
                return True

        # …neither is this
        txts = ('title', 'lead')

        for t in txts:
            for key in safe_format_keys(getattr(configuration, t, '')):
                if fid == as_internal_id(key):
                    return True

        # also include fields which are used as keywords
        if fid in (as_internal_id(v) for v in configuration.keywords):
            return True

        # check if the field is the thumbnail
        if fid == as_internal_id(configuration.thumbnail):
            return True

        return False

    @property
    def default_marker_color(self):
        return self.request.app.org.theme_options.get('primary-color')\
            or user_options['primary-color']

    @property
    def marker_color(self):
        if self.marker_color_value.data:
            return self.marker_color_value.data.get_hex()

    @marker_color.setter
    def marker_color(self, value):
        self.marker_color_value.data = Color(
            value or self.default_marker_color)

    @property
    def configuration(self):
        content_fields = list(self.extract_field_ids(self.content_fields))
        content_hide_labels = list(
            self.extract_field_ids(self.content_hide_labels))
        contact_fields = list(self.extract_field_ids(self.contact_fields))
        keyword_fields = list(self.extract_field_ids(self.keyword_fields))
        thumbnails = list(self.extract_field_ids(self.show_as_thumbnails))

        order_format = self.data[
            self.order.data == 'by-title' and 'title_format' or 'order_format'
        ]

        return DirectoryConfiguration(
            title=self.title_format.data,
            lead=self.lead_format.data,
            order=safe_format_keys(order_format),
            keywords=keyword_fields,
            searchable=content_fields + contact_fields,
            display={
                'content': content_fields,
                'contact': contact_fields,
                'content_hide_labels': content_hide_labels
            },
            direction=self.order_direction.data,
            link_pattern=self.link_pattern.data,
            link_title=self.link_title.data,
            link_visible=self.link_visible.data,
            thumbnail=(
                self.thumbnail.data and self.thumbnail.data.splitlines()[0]
            ),
            address_block_title=(
                self.address_block_title_type.data == 'fixed'
                and self.address_block_title.data
                or None
            ),
            show_as_thumbnails=thumbnails
        )

    @configuration.setter
    def configuration(self, cfg):

        def join(attr):
            return getattr(cfg, attr, None) and '\n'.join(getattr(cfg, attr))

        self.title_format.data = cfg.title
        self.lead_format.data = cfg.lead or ''
        self.content_fields.data = '\n'.join(cfg.display.get('content', ''))
        self.content_hide_labels.data = '\n'.join(
            cfg.display.get('content_hide_labels', ''))
        self.contact_fields.data = '\n'.join(cfg.display.get('contact', ''))
        self.keyword_fields.data = join('keywords')
        self.order_direction.data = cfg.direction == 'desc' and 'desc' or 'asc'
        self.link_pattern.data = cfg.link_pattern
        self.link_title.data = cfg.link_title
        self.link_visible.data = cfg.link_visible
        self.thumbnail.data = cfg.thumbnail
        self.show_as_thumbnails.data = join('show_as_thumbnails')

        if safe_format_keys(cfg.title) == cfg.order:
            self.order.data = 'by-title'
        else:
            self.order.data = 'by-format'
            self.order_format.data = ''.join(f'[{key}]' for key in cfg.order)

        if cfg.address_block_title:
            self.address_block_title_type.data = 'fixed'
            self.address_block_title.data = cfg.address_block_title
        else:
            self.address_block_title_type.data = 'auto'
            self.address_block_title.data = ""

    def populate_obj(self, obj):
        super().populate_obj(obj, exclude={
            'configuration',
            'order',
        })

        obj.configuration = self.configuration

        if self.marker_color_type.data == 'default':
            obj.marker_color = None
        else:
            obj.marker_color = self.marker_color

    def process_obj(self, obj):
        self.configuration = obj.configuration

        if obj.marker_color:
            self.marker_color_type.data = 'custom'
            self.marker_color = obj.marker_color
        else:
            self.marker_color_type.data = 'default'
            self.marker_color = self.default_marker_color


class DirectoryForm(merge_forms(DirectoryBaseForm, PaymentMethodForm)):

    payment_method_args = PaymentMethodForm.payment_method.kwargs.copy()
    payment_method_args['fieldset'] = _("New entries")
    payment_method_args['depends_on'] = (
        'enable_submissions', 'y', 'price', 'paid')

    payment_method = RadioField(**payment_method_args)


DirectoryForm = move_fields(
    DirectoryForm, ('payment_method', ), after='currency')


class DirectoryImportForm(Form):

    import_config = RadioField(
        label=_("Apply directory configuration"),
        choices=(
            ('yes', _("Yes, import configuration and entries")),
            ('no', _("No, only import entries"))
        ),
        default='no',
        validators=[validators.InputRequired()]
    )

    mode = RadioField(
        label=_("Mode"),
        choices=(
            ('new', _("Only import new entries")),
            ('replace', _("Replace all entries")),
        ),
        default='new',
        validators=[validators.InputRequired()]
    )

    zip_file = UploadField(
        label=_("Import"),
        validators=[
            validators.DataRequired(),
            WhitelistedMimeType({
                'application/zip',
                'application/octet-stream'
            }),
            FileSizeLimit(500 * 1024 * 1024)
        ],
        render_kw=dict(force_simple=True)
    )

    @staticmethod
    def clear_entries(session, target):
        for existing in target.entries:
            session.delete(existing)

        target.entries.clear()
        session.flush()

    def run_import(self, target):
        session = object_session(target)

        count = 0

        def count_entry(entry):
            nonlocal count
            count += 1

        if self.mode.data == 'replace':
            self.clear_entries(session, target)

        archive = DirectoryZipArchive.from_buffer(self.zip_file.file)
        archive.read(
            target=target,
            skip_existing=True,
            limit=100,
            apply_metadata=self.import_config.data == 'yes',
            after_import=count_entry
        )

        return count
