import re
import textwrap

import onegov.core
import os.path
import pytest
import transaction

from onegov.core import utils
from onegov.core.custom import json
from onegov.core.errors import AlreadyLockedError
from onegov.core.orm import SessionManager
from onegov.core.orm.types import HSTORE
from onegov.core.utils import Bunch, linkify_phone, _phone_ch, to_html_ul
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from unittest.mock import patch
from uuid import uuid4
from yubico_client import Yubico


def test_normalize_for_url():
    assert utils.normalize_for_url('asdf') == 'asdf'
    assert utils.normalize_for_url('Asdf') == 'asdf'
    assert utils.normalize_for_url('A S d f') == 'a-s-d-f'
    assert utils.normalize_for_url('far  away') == 'far-away'
    assert utils.normalize_for_url('währung') == 'waehrung'
    assert utils.normalize_for_url('grün') == 'gruen'
    assert utils.normalize_for_url('rötlich') == 'roetlich'
    assert utils.normalize_for_url('one/two') == 'one-two'
    assert utils.normalize_for_url('far / away') == 'far-away'
    assert utils.normalize_for_url('far <away>') == 'far-away'
    assert utils.normalize_for_url('far (away)') == 'far-away'
    assert utils.normalize_for_url('--ok--') == 'ok'
    assert utils.normalize_for_url('a...b..c.d') == 'a-b-c-d'


def test_lchop():
    assert utils.lchop('foobar', 'foo') == 'bar'
    assert utils.lchop('foobar', 'bar') == 'foobar'


def test_rchop():
    assert utils.rchop('foobar', 'foo') == 'foobar'
    assert utils.rchop('foobar', 'bar') == 'foo'
    assert utils.rchop('https://www.example.org/ex/amp/le', '/ex/amp/le') \
        == 'https://www.example.org'


def test_touch(temporary_directory):
    path = os.path.join(temporary_directory, 'test.txt')

    assert not os.path.isfile(path)

    utils.touch(path)

    assert os.path.isfile(path)

    with open(path, 'w') as f:
        f.write('asdf')

    utils.touch(path)

    with open(path, 'r') as f:
        assert f.read() == 'asdf'


def test_module_path():
    path = utils.module_path('onegov.core', 'utils.py')
    assert path == utils.module_path(onegov.core, 'utils.py')
    assert path == utils.module_path(onegov.core, '/utils.py')
    assert os.path.isfile(path)

    with pytest.raises(AssertionError):
        utils.module_path(onegov.core, '../passwd')


valid_test_phone_numbers = [
    '+41 44 453 45 45',
    '+41 79434 3254',
    '+41     79434     3254',
    '+4179434 3254',
    '004179434 3254',
    '044 302 35 87',
    '079 720 55 03',
    '0797205503',
    '0413025643',
    '041 324 4321',
]

# +041 324 4321 will treat + like a normal text around

invalid_test_phone_numbers = [
    '<a href="tel:061 444 44 44">061 444 44 44</a>',
    '">+41 44 453 45 45',
    'some text',
    '+31 654 32 54',
    '+0041 543 44 44',
    '0041-24400321',
    '0043 555 32 43'
]


@pytest.mark.parametrize("number", valid_test_phone_numbers)
def test_phone_regex_groups_valid(number):
    gr = re.search(_phone_ch, number)
    assert gr.group(0)
    assert gr.group(1)
    assert gr.group(2)


@pytest.mark.parametrize("number", valid_test_phone_numbers)
def test_phone_linkify_valid(number):
    r = linkify_phone(number)
    number = utils.remove_duplicate_whitespace(number)
    wanted = f'<a href="tel:{number}">{number}</a>'
    assert r == wanted
    # Important !
    assert linkify_phone(wanted) == wanted


@pytest.mark.parametrize("number", invalid_test_phone_numbers)
def test_phone_linkify_invalid(number):
    r = linkify_phone(number)
    assert r == number


def test_linkify():
    # this is really bleach's job, but we want to run the codepath anyway
    assert utils.linkify('info@example.org')\
        == '<a href="mailto:info@example.org">info@example.org</a>'
    assert utils.linkify('https://google.ch')\
        == '<a href="https://google.ch" rel="nofollow">https://google.ch</a>'

    # by default, linkify sanitizes the text before linkifying it
    assert utils.linkify('info@example.org<br>')\
        == '<a href="mailto:info@example.org">info@example.org</a>&lt;br&gt;'

    # we can disable that however
    assert utils.linkify('info@example.org<br>', escape=False)\
        == '<a href="mailto:info@example.org">info@example.org</a><br>'

    # test a longer html string with valid phone number
    tel_nr = valid_test_phone_numbers[0]
    text = f'2016/2019<br>{tel_nr}'
    assert utils.linkify(text, escape=False) ==\
           f'2016/2019<br><a href="tel:{tel_nr}">{tel_nr}</a>'


@pytest.mark.parametrize("tel", [
    ('Tel. +41 41 728 33 11',
     'Tel. <a href="tel:+41 41 728 33 11">+41 41 728 33 11</a>'),
    ('\nTel. +41 41 728 33 11\n',
     '\nTel. <a href="tel:+41 41 728 33 11">+41 41 728 33 11</a>\n'),

])
def test_linkify_with_phone(tel):
    assert utils.linkify(tel[0], escape=False) == tel[1]
    assert utils.linkify(tel[0], escape=True) == tel[1]


def test_linkify_with_phone_newline():
    assert utils.linkify('Foo\n041 123 45 67') == (
        'Foo\n<a href="tel:041 123 45 67">041 123 45 67</a>'
    )


def test_increment_name():
    assert utils.increment_name('test') == 'test-1'
    assert utils.increment_name('test-2') == 'test-3'
    assert utils.increment_name('test2') == 'test2-1'
    assert utils.increment_name('test-1-1') == 'test-1-2'


def test_ensure_scheme():
    assert utils.ensure_scheme(None) is None
    assert utils.ensure_scheme('seantis.ch') == 'http://seantis.ch'
    assert utils.ensure_scheme('seantis.ch', 'https') == 'https://seantis.ch'

    assert utils.ensure_scheme('google.ch?q=onegov.cloud')\
        == 'http://google.ch?q=onegov.cloud'

    assert utils.ensure_scheme('https://abc.xyz') == 'https://abc.xyz'


def test_remove_duplicate_whitespace():
    assert utils.remove_duplicate_whitespace('foo  bar') == 'foo bar'
    assert utils.remove_duplicate_whitespace('  foo  bar  ') == ' foo bar '
    assert utils.remove_duplicate_whitespace('       foo    bar') == ' foo bar'


def test_is_uuid():
    assert not utils.is_uuid(None)
    assert not utils.is_uuid('')
    assert not utils.is_uuid('asdf')
    assert not utils.is_uuid(uuid4().hex + 'x')
    assert utils.is_uuid(uuid4())
    assert utils.is_uuid(str(uuid4()))
    assert utils.is_uuid(uuid4().hex)


def test_is_non_string_iterable():
    assert utils.is_non_string_iterable([])
    assert utils.is_non_string_iterable(tuple())
    assert utils.is_non_string_iterable({})
    assert not utils.is_non_string_iterable('abc')
    assert not utils.is_non_string_iterable(b'abc')
    assert not utils.is_non_string_iterable(None)


def test_relative_url():
    assert utils.relative_url('https://www.google.ch/test') == '/test'
    assert utils.relative_url('https://usr:pwd@localhost:443/test') == '/test'
    assert utils.relative_url('/test') == '/test'
    assert utils.relative_url('/test?x=1&y=2') == '/test?x=1&y=2'
    assert utils.relative_url('/test?x=1&y=2#link') == '/test?x=1&y=2#link'


def test_is_subpath():
    assert utils.is_subpath('/', '/test')
    assert utils.is_subpath('/asdf', '/asdf/asdf')
    assert not utils.is_subpath('/asdf/', '/asdf')
    assert not utils.is_subpath('/a', '/b')
    assert not utils.is_subpath('/a', '/a/../b')


def test_is_sorted():
    assert utils.is_sorted('abc')
    assert not utils.is_sorted('aBc')
    assert utils.is_sorted('aBc', key=lambda i: i.lower())
    assert not utils.is_sorted('321')
    assert utils.is_sorted('321', reverse=True)


def test_get_unique_hstore_keys(postgres_dsn):

    Base = declarative_base()

    class Document(Base):
        __tablename__ = 'documents'

        id = Column(Integer, primary_key=True)
        _tags = Column(HSTORE, nullable=True)

        @property
        def tags(self):
            return set(self._tags.keys()) if self._tags else set()

        @tags.setter
        def tags(self, value):
            self._tags = {k: '' for k in value} if value else None

    mgr = SessionManager(postgres_dsn, Base)
    mgr.set_current_schema('foo')

    assert utils.get_unique_hstore_keys(mgr.session(), Document._tags) == set()

    mgr.session().add(Document(tags=None))
    mgr.session().add(Document(tags=['foo', 'bar']))
    mgr.session().add(Document(tags=['foo', 'baz']))

    transaction.commit()

    assert utils.get_unique_hstore_keys(mgr.session(), Document._tags) == {
        'foo', 'bar', 'baz'
    }


def test_remove_repeated_spaces():

    assert utils.remove_repeated_spaces('  ') == ' '
    assert utils.remove_repeated_spaces('a b') == 'a b'
    assert utils.remove_repeated_spaces('a       b') == 'a b'
    assert utils.remove_repeated_spaces((' x  ')) == ' x '


def test_post_thread(session):
    with patch('urllib.request.urlopen') as urlopen:
        url = 'https://example.com/post'
        data = {'key': 'ä$j', 'b': 2}
        data = json.dumps(data).encode('utf-8')
        headers = (
            ('Content-type', 'application/json; charset=utf-8'),
            ('Content-length', len(data))
        )

        thread = utils.PostThread(url, data, headers)
        thread.start()
        thread.join()

        assert urlopen.called
        assert urlopen.call_args[0][0].get_full_url() == url
        assert urlopen.call_args[0][1] == data
        assert urlopen.call_args[0][0].headers == dict(headers)


def test_binary_dictionary():

    d = utils.binary_to_dictionary(b'foobar')
    assert d['filename'] is None
    assert d['mimetype'] == 'text/plain'
    assert d['size'] == 6

    d = utils.binary_to_dictionary(b'foobar', 'readme.txt')
    assert d['filename'] == 'readme.txt'
    assert d['mimetype'] == 'text/plain'
    assert d['size'] == 6

    assert utils.dictionary_to_binary(d) == b'foobar'


def test_safe_format():
    fmt = utils.safe_format

    assert fmt('hello [user]', {'user': 'admin'}) == 'hello admin'
    assert fmt('[ix]: [ix]', {'ix': 1}) == '1: 1'
    assert fmt('[[user]]', {'user': 'admin'}) == '[user]'
    assert fmt('[[[user]]]', {'user': 'admin'}) == '[admin]'
    assert fmt('[asdf]', {}) == ''
    assert fmt('[foo]', {'FOO': 'bar'}, adapt=str.upper) == 'bar'

    with pytest.raises(RuntimeError) as e:
        fmt('[foo[bar]]', {'foo[bar]': 'baz'})

    assert 'bracket inside bracket' in str(e.value)

    with pytest.raises(RuntimeError) as e:
        fmt('[secret]', {'secret': object()})

    assert 'type' in str(e.value)

    with pytest.raises(RuntimeError) as e:
        fmt('[asdf', {})

    assert 'Uneven' in str(e.value)

    with pytest.raises(RuntimeError) as e:
        fmt('[foo]', {}, raise_on_missing=True)

    assert 'is unknown' in str(e.value)


def test_local_lock():
    with utils.local_lock('foo', 'bar'):
        with pytest.raises(AlreadyLockedError):
            with utils.local_lock('foo', 'bar'):
                pass


def test_is_valid_yubikey_otp():

    assert not utils.is_valid_yubikey(
        client_id='abc',
        secret_key='dGhlIHdvcmxkIGlzIGNvbnRyb2xsZWQgYnkgbGl6YXJkcyE=',
        expected_yubikey_id='ccccccbcgujx',
        yubikey='ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded'
    )

    with patch.object(Yubico, 'verify') as verify:
        verify.return_value = True

        assert utils.is_valid_yubikey(
            client_id='abc',
            secret_key='dGhlIHdvcmxkIGlzIGNvbnRyb2xsZWQgYnkgbGl6YXJkcyE=',
            expected_yubikey_id='ccccccbcgujh',
            yubikey='ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded'
        )


def test_is_valid_yubikey_format():
    assert utils.is_valid_yubikey_format('ccccccdefghd')
    assert utils.is_valid_yubikey_format('cccccccdefg' * 4)
    assert not utils.is_valid_yubikey_format('ccccccdefghx')


def test_yubikey_otp_to_serial():
    assert utils.yubikey_otp_to_serial(
        'ccccccdefghdefghdefghdefghdefghdefghdefghklv') == 2311522
    assert utils.yubikey_otp_to_serial("ceci n'est pas une yubikey") is None


def test_yubikey_public_id():
    assert utils.yubikey_public_id(
        'ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded'
    ) == 'ccccccbcgujh'

    with pytest.raises(TypeError):
        utils.yubikey_public_id(None)


def test_paragraphify():
    assert utils.paragraphify('') == ''
    assert utils.paragraphify('\n') == ''
    assert utils.paragraphify('foo') == '<p>foo</p>'
    assert utils.paragraphify('foo\nbar') == '<p>foo<br>bar</p>'
    assert utils.paragraphify('foo\n\nbar') == '<p>foo</p><p>bar</p>'
    assert utils.paragraphify('foo\r\nbar') == '<p>foo<br>bar</p>'
    assert utils.paragraphify('foo\r\n\r\nbar') == '<p>foo</p><p>bar</p>'


def test_bunch():
    bunch = Bunch(a=1, b=2)
    assert bunch.a == 1
    assert bunch.b == 2

    assert (Bunch() == Bunch()) is True
    assert (Bunch(x=1) == Bunch()) is False
    assert (Bunch(x=1) == Bunch(x=1)) is True
    assert (Bunch(x=1) == Bunch(x=2)) is False
    assert (Bunch(x=1, y=2) == Bunch(x=1, y=2)) is True
    assert (Bunch(x=1, y=2) == Bunch(x=2, y=2)) is False
    assert (Bunch(x=1, y=2) == Bunch(x=1, y=3)) is False

    assert (Bunch() != Bunch()) is False
    assert (Bunch(x=1) != Bunch()) is True
    assert (Bunch(x=1) != Bunch(x=1)) is False
    assert (Bunch(x=1) != Bunch(x=2)) is True
    assert (Bunch(x=1, y=2) != Bunch(x=1, y=2)) is False
    assert (Bunch(x=1, y=2) != Bunch(x=2, y=2)) is True
    assert (Bunch(x=1, y=2) != Bunch(x=1, y=3)) is True


def test_to_html_ul():

    def li(*args):
        if len(args) > 1:
            return "".join(f'<li>{i}</li>' for i in args)
        return f'<li>{args[0]}</li>'

    text = "\n".join(('Title', 'A'))
    assert to_html_ul(text) == f'<ul>{li("Title", "A")}</ul>'

    text = "\n".join(('- Title', '-A', '-B'))
    li_inner = li('Title', 'A', 'B')
    assert to_html_ul(text) == f'<ul class="bulleted">{li_inner}</ul>'

    # two lists
    text = "\n".join(('-A', 'B'))
    assert to_html_ul(text) == f'<ul class="bulleted">{li("A")}</ul>' \
                               f'<ul>{li("B")}</ul>'
    text = "\n".join(('A', '-B'))
    assert to_html_ul(text) == f'<ul>{li("A")}</ul>' \
                               f'<ul class="bulleted">{li("B")}</ul>'

    # double new lines are ignored
    text = "\n".join(('A', '', '', 'B'))
    assert to_html_ul(text) == f'<ul>{li("A", "B")}</ul>'

    text = "\n".join(('A', '', '', '-B'))
    assert to_html_ul(text) == f'<ul>{li("A")}</ul>' \
                               f'<ul class="bulleted">{li("B")}</ul>'
