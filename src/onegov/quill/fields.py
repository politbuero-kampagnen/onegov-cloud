from bleach.sanitizer import Cleaner
from onegov.quill.widgets import QuillInput
from onegov.quill.widgets import TAGS
from wtforms import TextAreaField


class QuillField(TextAreaField):
    """ A textfield using the quill editor and with integrated sanitation.

    Allows to specifiy which tags to use in the editor and for sanitation.
    Available tags are: strong, em, s, a, ol, ul, h1, h2, h3, blockquote, pre.
    (p and br tags are always possible).

    """

    def __init__(self, **kwargs):
        tags = kwargs.pop('tags', TAGS)
        tags = [tag for tag in tags if tag in TAGS]

        super(TextAreaField, self).__init__(**kwargs)

        self.widget = QuillInput(tags=tags)

        tags += ['p', 'br']
        tags += ['li'] if 'ol' in tags or 'ul' in tags else []
        attributes = {'a': 'href'} if 'a' in tags else {}
        self.cleaner = Cleaner(tags=tags, attributes=attributes, strip=True)

    def pre_validate(self, form):
        self.data = self.cleaner.clean(self.data or '')

    def translate(self, request):
        self.widget.placeholder_label = request.translate(
            self.widget.placeholder_label
        )
