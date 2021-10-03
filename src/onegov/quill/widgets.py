from random import choice
from wtforms.widgets import HiddenInput
from wtforms.widgets.core import HTMLString


HEADINGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
LISTS = ['ol', 'ul']
TAGS = ['strong', 'em', 's', 'a'] + HEADINGS + LISTS + ['blockquote', 'pre']


class QuillInput(HiddenInput):
    """
    Renders the text content as hidden input and adds a container for the
    editor.


    """

    def __init__(self, **kwargs):
        tags = kwargs.pop('tags', TAGS)
        tags = [tag for tag in tags if tag in TAGS]

        super(QuillInput, self).__init__(**kwargs)

        self.id = ''.join(choice('abcdefghi') for i in range(8))

        formats = {
            'strong': "'bold'",
            'em': "'italic'",
            's': "'strike'",
            'a': "'link'",
            'h1': "'header'",
            'h2': "'header'",
            'h3': "'header'",
            'h4': "'header'",
            'h5': "'header'",
            'h6': "'header'",
            'ol': "'list'",
            'ul': "'list'",
            'blockquote': "'blockquote'",
            'pre': "'code-block'",
        }
        self.formats = [formats[tag] for tag in tags if tag in formats]
        self.formats = [
            fmt for (i, fmt) in enumerate(self.formats)
            if fmt not in self.formats[0:i]
        ]

        toolbar = {
            'strong': "'bold'",
            'em': "'italic'",
            's': "'strike'",
            'a': "'link'",
            'h1': "{'header': 1}",
            'h2': "{'header': 2}",
            'h3': "{'header': 3}",
            'h4': "{'header': 4}",
            'h5': "{'header': 5}",
            'h6': "{'header': 6}",
            'ol': "{'list': 'ordered'}",
            'ul': "{'list': 'bullet'}",
            'blockquote': "'blockquote'",
            'pre': "'code-block'",
        }
        self.toolbar = [toolbar[tag] for tag in tags if tag in toolbar]

    def __call__(self, field, **kwargs):
        input_id = f'quill-input-{self.id}'
        kwargs['id'] = input_id
        input = super(QuillInput, self).__call__(field, **kwargs)

        container_id = f'quill-container-{self.id}'
        scroll_container_id = f'scrolling-container-{self.id}'
        formats = ', '.join(self.formats)
        toolbar = ', '.join(self.toolbar)

        return HTMLString(f"""
            <div style="position:relative">
                <div class="scrolling-container" id="{scroll_container_id}">
                  <div class="quill-container" id="{container_id}"></div>
                </div>
            </div>
            <script>
                window.addEventListener('load', function () {{
                    var input = document.getElementById('{input_id}');
                    var quill = new Quill('#{container_id}', {{
                        formats: [{formats}],
                        modules: {{
                            toolbar: [{toolbar}],
                        }},
                        scrollingContainer: '#{scroll_container_id}',
                        theme: 'snow'
                    }});
                    quill.clipboard.dangerouslyPasteHTML(input.value);
                    quill.on('text-change', function() {{
                        input.value = quill.root.innerHTML
                    }});
                }});
            </script>
            {input}
        """)
