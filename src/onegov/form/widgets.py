import chameleon
import humanize

from contextlib import suppress
from html import escape
from morepath.error import LinkError
from onegov.file.utils import IMAGE_MIME_TYPES_AND_SVG
from onegov.form import _
from wtforms.widgets import FileInput
from wtforms.widgets import ListWidget
from wtforms.widgets import Select
from wtforms.widgets import TextInput
from wtforms.widgets.core import HTMLString, html_params


class OrderedListWidget(ListWidget):
    """ Extends the default list widget with automated ordering using the
    translated text of each element.

    """

    def __call__(self, field, **kwargs):

        # ListWidget expects a field internally, but it will only use
        # its id property and __iter__ method, so we can get away
        # with passing a fake field with an id and an iterator.
        #
        # It's not great, since we have to assume internal knowledge,
        # but builting a new field or changing the existing one would
        # require even more knowledge, so this is the better approach
        #
        # We also need to call each field once so it gets hooked up with
        # our translation machinary
        ordered = [subfield for subfield in field]
        ordered.sort(key=lambda f: (f(), str(f.label.text))[1])

        class FakeField(object):

            id = field.id

            def __iter__(self):
                return iter(ordered)

        return super().__call__(FakeField(), **kwargs)


class MultiCheckboxWidget(ListWidget):
    """ The default list widget with the label behind the checkbox. """

    def __init__(self, *args, **kwargs):
        kwargs['prefix_label'] = False
        super().__init__(*args, **kwargs)


class OrderedMultiCheckboxWidget(MultiCheckboxWidget, OrderedListWidget):
    """ The sorted list widget with the label behind the checkbox. """
    pass


class CoordinateWidget(TextInput):
    """ Widget containing the coordinates for the
    :class:`onegov.form.fields.CoordinateField` class.

    Basically a text input with a class. Meant to be enhanced on the browser
    using javascript.

    """

    def __call__(self, field, **kwargs):
        kwargs['class_'] = (kwargs.get('class_', '') + ' coordinate').strip()
        return super().__call__(field, **kwargs)


class UploadWidget(FileInput):
    """ An upload widget for the :class:`onegov.form.fields.UploadField` class,
    which supports keeping, removing and replacing already uploaded files.

    This is necessary as file inputs are read-only on the client and it's
    therefore rather easy for users to lose their input otherwise (e.g. a
    form with a file is rejected because of some mistake - the file disappears
    once the response is rendered on the client).

    """

    def image_source(self, field):
        """ Returns the image source url if the field points to an image and
        if it can be done (it looks like it's possible, but I'm not super
        sure this is always possible).

        """

        if not hasattr(field.meta, 'request'):
            return

        if not field.data:
            return

        if not field.data.get('mimetype', None) in IMAGE_MIME_TYPES_AND_SVG:
            return

        if not hasattr(field, 'object_data'):
            return

        if not field.object_data:
            return

        with suppress(LinkError, AttributeError):
            return field.meta.request.link(field.object_data)

    def __call__(self, field, **kwargs):
        force_simple = kwargs.pop('force_simple', False)
        input_html = super().__call__(field, **kwargs)

        if force_simple or field.errors or not field.data:
            return HTMLString("""
                <div class="upload-widget without-data">
                    {}
                </div>
            """.format(input_html))
        else:
            src = self.image_source(field)

            if not src:
                preview = ''
            else:
                preview = f"""
                    <div class="uploaded-image"><img src="{src}"></div>
                """

            return HTMLString("""
                <div class="upload-widget with-data">
                    <p>{existing_file_label}: {filename} ({filesize}) ✓</p>

                    {preview}

                    <ul>
                        <li>
                            <input type="radio" id="{name}-0" name="{name}"
                                   value="keep" checked="">
                            <label for="{name}-0">{keep_label}</label>
                        </li>
                        <li>
                            <input type="radio" id="{name}-1" name="{name}"
                                   value="delete">
                            <label for="{name}-1">{delete_label}</label>
                        </li>
                        <li>
                            <input type="radio" id="{name}-2" name="{name}"
                                   value="replace">
                            <label for="{name}-2">{replace_label}</label>
                            <div>
                                <label>
                                    <div data-depends-on="{name}/replace"
                                         data-hide-label="false">
                                        {input_html}
                                    </div>
                                </label>
                            </div>
                        </li>
                    </ul>
                </div>
            """.format(
                # be careful, we do our own html generation here without any
                # safety harness - we need to carefully escape values the user
                # might supply
                filesize=humanize.naturalsize(field.data['size']),
                filename=escape(field.data['filename'], quote=True),
                name=field.id,
                input_html=input_html,
                existing_file_label=field.gettext(_('Uploaded file')),
                keep_label=field.gettext(_('Keep file')),
                delete_label=field.gettext(_('Delete file')),
                replace_label=field.gettext(_('Replace file')),
                preview=preview,
            ))


class TagsWidget(TextInput):
    # for use with https://github.com/developit/tags-input
    input_type = 'tags'


class IconWidget(TextInput):

    iconfont = 'FontAwesome'
    icons = {
        'FontAwesome': (
            ('&#xf111', 'fa fa-circle'),
            ('&#xf005', 'fa fa-star'),
            ('&#xf06a', 'fa fa-exclamation-circle'),
            ('&#xf059', 'fa fa-question-circle'),
            ('&#xf05e', 'fa fa-ban'),
            ('&#xf1b9', 'fa fa-car'),
            ('&#xf238', 'fa fa-train'),
            ('&#xf206', 'fa fa-bicycle'),
            ('&#xf291', 'fa fa-shopping-basket'),
            ('&#xf1b0', 'fa fa-paw'),
            ('&#xf1ae', 'fa fa-child'),
            ('&#xf06d', 'fa fa-fire'),
            ('&#xf1f8', 'fa fa-trash'),
            ('&#xf236', 'fa fa-hotel'),
            ('&#xf0f4', 'fa fa-coffee'),
            ('&#xf017', 'fa fa-clock'),
        ),
        'Font Awesome 5 Free': (
            ('&#xf111', 'fas fa-circle'),
            ('&#xf005', 'fas fa-star'),
            ('&#xf06a', 'fas fa-exclamation-circle'),
            ('&#xf059', 'fas fa-question-circle'),
            ('&#xf05e', 'fas fa-ban'),
            ('&#xf1b9', 'fas fa-car'),
            ('&#xf238', 'fas fa-train'),
            ('&#xf206', 'fas fa-bicycle'),
            ('&#xf291', 'fas fa-shopping-basket'),
            ('&#xf1b0', 'fas fa-paw'),
            ('&#xf1ae', 'fas fa-child'),
            ('&#xf06d', 'fas fa-fire'),
            ('&#xf1f8', 'fas fa-trash'),
            ('&#xf594', 'fas fa-hotel'),
            ('&#xf0f4', 'fas fa-coffee'),
            ('&#xf017', 'fas fa-clock')
        )
    }

    @property
    def template(self):
        return chameleon.PageTemplate("""
        <div class="icon-widget">
            <ul style="font-family: ${iconfont}">
                <li
                    tal:repeat="icon icons"
                    tal:content="structure icon[0]"
                    style="font-weight: ${font_weight(icon)}"
                />
            </ul>
            <input type="hidden" name="${id}" value="${structure: value}">
        </div>
    """)

    def __call__(self, field, **kwargs):
        iconfont = kwargs.pop('iconfont', self.iconfont)
        icons = kwargs.pop('icons', self.icons[iconfont])

        if ' ' in iconfont:
            iconfont = f"'{iconfont}'"

        def font_weight(icon):
            if icon[1].startswith('fas'):
                return '900'
            return 'regular'

        return HTMLString(self.template.render(
            iconfont=iconfont,
            icons=icons,
            id=field.id,
            value=field.data or icons[0][0],
            font_weight=font_weight
        ))


class ChosenSelectWidget(Select):

    def __call__(self, field, **kwargs):
        kwargs['class_'] = '{} chosen-select'.format(
            kwargs.get('class_', '')
        ).strip()
        kwargs['data-placeholder'] = field.gettext(_("Select an Option"))
        kwargs['data-no_results_text'] = field.gettext(_("No results match"))
        if self.multiple:
            kwargs['data-placeholder'] = field.gettext(
                _("Select Some Options")
            )

        return super(ChosenSelectWidget, self).__call__(field, **kwargs)


class PreviewWidget(object):
    """ A widget that displays the html of a specific view whenver there's
    a change in other fields. JavaScript is used to facilitate this.

    """

    template = chameleon.PageTemplate("""
        <div class="form-preview-widget"
             data-url="${url or ''}"
             data-fields="${','.join(fields)}"
             data-events="${','.join(events)}"
             data-display="${display}">
        </div>
    """)

    def __call__(self, field, **kwargs):
        field.meta.request.include('preview-widget-handler')

        return HTMLString(self.template.render(
            url=callable(field.url) and field.url(field.meta) or field.url,
            fields=field.fields,
            events=field.events,
            display=field.display,
        ))


class PanelWidget(object):
    """ A widget that displays the field's text as panel (no input). """

    template = chameleon.PageTemplate(
        """<div class="panel ${kind}">${text}</div>"""
    )

    def __call__(self, field, **kwargs):
        text = self.template.render(
            kind=field.kind,
            text=field.meta.request.translate(field.text),
        )
        text = text.replace('">', '" ' + html_params(**kwargs) + '>')
        text = text.replace('\n', '<br>')
        return HTMLString(text)


class HoneyPotWidget(TextInput):
    """ A widget that displays the input normally not visible to the user. """

    def __call__(self, field, **kwargs):
        field.meta.request.include('lazy-wolves')
        kwargs['class_'] = (kwargs.get('class_', '') + ' lazy-wolves').strip()
        return super().__call__(field, **kwargs)
