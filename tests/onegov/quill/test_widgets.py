from onegov.form import Form
from onegov.quill.fields import QuillField
from onegov.quill.widgets import ALL_TAGS
from onegov.quill.widgets import QuillInput


def test_widget_initalization():
    input = QuillInput()
    assert input.formats == [
        "'bold'",
        "'italic'",
        "'strike'",
        "'link'",
        "'header'",
        "'list'",
        "'blockquote'",
        "'code-block'"
    ]
    assert input.toolbar == [
        "'bold'",
        "'italic'",
        "'strike'",
        "'link'",
        "{'header': 2}",
        "{'header': 3}",
        "{'list': 'ordered'}",
        "{'list': 'bullet'}",
        "'blockquote'",
        "'code-block'"
    ]

    input = QuillInput(tags=ALL_TAGS)
    assert input.formats == [
        "'bold'",
        "'italic'",
        "'strike'",
        "'link'",
        "'header'",
        "'list'",
        "'blockquote'",
        "'code-block'"
    ]
    assert input.toolbar == [
        "'bold'",
        "'italic'",
        "'strike'",
        "'link'",
        "{'header': 1}",
        "{'header': 2}",
        "{'header': 3}",
        "{'header': 4}",
        "{'header': 5}",
        "{'header': 6}",
        "{'list': 'ordered'}",
        "{'list': 'bullet'}",
        "'blockquote'",
        "'code-block'"
    ]

    input = QuillInput(tags=['strong', 'ul'])
    assert input.formats == ["'bold'", "'list'"]
    assert input.toolbar == ["'bold'", "{'list': 'bullet'}"]

    input = QuillInput(tags=['em', 'ol'])
    assert input.formats == ["'italic'", "'list'"]
    assert input.toolbar == ["'italic'", "{'list': 'ordered'}"]

    input = QuillInput(tags=['strong'])
    assert input.formats == ["'bold'"]
    assert input.toolbar == ["'bold'"]

    input = QuillInput(tags=['s'])
    assert input.formats == ["'strike'"]
    assert input.toolbar == ["'strike'"]

    input = QuillInput(tags=['a'])
    assert input.formats == ["'link'"]
    assert input.toolbar == ["'link'"]

    input = QuillInput(tags=['blockquote'])
    assert input.formats == ["'blockquote'"]
    assert input.toolbar == ["'blockquote'"]

    input = QuillInput(tags=['pre'])
    assert input.formats == ["'code-block'"]
    assert input.toolbar == ["'code-block'"]

    input = QuillInput(tags=['h1'])
    assert input.formats == ["'header'"]
    assert input.toolbar == ["{'header': 1}"]

    input = QuillInput(tags=['h3', 'h5'])
    assert input.formats == ["'header'"]
    assert input.toolbar == ["{'header': 3}", "{'header': 5}"]

    input = QuillInput(tags=['i'])
    assert input.formats == []
    assert input.toolbar == []


def test_widget_render():
    form = Form()
    field = QuillField()
    field = field.bind(form, 'html')
    field.data = 'xxx'

    input = QuillInput()
    text = input(field)
    assert f'quill-container-{input.id}' in text
    assert f'quill-input-{input.id}' in text
    assert (
        "'bold', "
        "'italic', "
        "'strike', "
        "'link', "
        "'header', "
        "'list', "
        "'blockquote', "
        "'code-block'"
    ) in text
    assert (
        "'bold', "
        "'italic', "
        "'strike', "
        "'link', "
        "{'header': 2}, "
        "{'header': 3}, "
        "{'list': 'ordered'}, "
        "{'list': 'bullet'}, "
        "'blockquote', "
        "'code-block'"
    ) in text

    input = QuillInput(tags=['em', 'ul'])
    text = input(field)
    assert f'quill-container-{input.id}' in text
    assert f'quill-input-{input.id}' in text
    assert "['italic', 'list']" in text
    assert "['italic', {'list': 'bullet'}]" in text
