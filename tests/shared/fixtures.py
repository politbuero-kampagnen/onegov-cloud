import os
import platform
import re

import port_for
import pytest
import shlex
import shutil
import subprocess
import tempfile
import transaction
import urllib3

from _pytest.monkeypatch import MonkeyPatch
from contextlib import suppress
from distutils.spawn import find_executable
from fs.tempfs import TempFS
from functools import lru_cache
from mirakuru import HTTPExecutor, TCPExecutor
from webdriver_manager.utils import ChromeType

from onegov.core.crypto import hash_password
from onegov.core.orm import Base, SessionManager
from pathlib import Path
from pytest_redis import factories
from redis import Redis
from selenium.webdriver.chrome.options import Options
from splinter import Browser
from sqlalchemy import create_engine, exc
from sqlalchemy.orm.session import close_all_sessions
from tests.shared.browser import ExtendedBrowser
from tests.shared.postgresql import Postgresql
from uuid import uuid4
from webdriver_manager.chrome import ChromeDriverManager


try:
    from elasticsearch import Elasticsearch
except ImportError:
    def Elasticsearch(*args, **kwargs):
        assert False, "Elasticsearch is not installed"


redis_path = find_executable('redis-server')
redis_server = factories.redis_proc(host='127.0.0.1', executable=redis_path)


def pytest_addoption(parser):
    parser.addoption('--nopg', action='store_true')


@pytest.fixture(scope='session')
def monkeysession(request):
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope='session', autouse=True)
def scan_onegov():
    import importscan
    import onegov
    importscan.scan(onegov, ignore=['.test', '.tests'])


@pytest.fixture(scope='session', autouse=True)
def treat_sqlalchemy_warnings_as_errors():
    """ All onegov models treat SQLAlchemy warnings as errors, because usually
    SQLAlchemy warnings are errors waiting to happen.

    """
    import warnings
    from sqlalchemy.exc import SAWarning
    warnings.simplefilter("error", SAWarning)


@pytest.fixture(scope='session', autouse=True)
def cache_password_hashing(monkeysession):
    """ Monkey-patch the password hashing/verification functions during tests
    for a big speed increase (we login with the same password over and over
    again).

    Changes to the auth are delicate, so we make sure this is only done during
    testing by having it here, instead of support some mechanism like this
    in onegov.core itself.

    So this dangerous code is not only inexistant in the core, it is also not
    present on the server because tests.shared is strictly a testing
    dependency and finally it is only run when invoked through pytest.

    """

    from passlib.hash import bcrypt_sha256

    verify = bcrypt_sha256.verify
    encrypt = bcrypt_sha256.encrypt

    @lru_cache(maxsize=32)
    def cached_verify(password, hash):
        return verify(password, hash)

    @lru_cache(maxsize=32)
    def cached_encrypt(password):
        return encrypt(password)

    monkeysession.setattr(
        'onegov.core.crypto.password.bcrypt_sha256.encrypt', cached_encrypt)
    monkeysession.setattr(
        'onegov.core.crypto.password.bcrypt_sha256.verify', cached_verify)


@pytest.fixture(scope="session")
def pg_default_preferred_versions():
    return ['9.6']


@pytest.fixture(scope="session")
def pg_preferred_versions(pg_default_preferred_versions):
    return os.environ.get('POSTGRES_VERSIONS', pg_default_preferred_versions)


@pytest.fixture(scope="session")
def postgres(pg_preferred_versions, pytestconfig):
    """ Starts a postgres server using `testing.postgresql \
    <https://pypi.python.org/pypi/testing.postgresql/>`_ once per test session.

    """
    if pytestconfig.getoption('nopg'):
        yield None
        return

    postgres_args = ' '.join((
        "-h 127.0.0.1",
        "-F",
        "-c logging_collector=off",
        "-c fsync=off",
        "-c full_page_writes=off",
    ))

    postgres = Postgresql(
        postgres_args=postgres_args,
        preferred_versions=pg_preferred_versions
    )
    yield postgres
    postgres.stop()


@pytest.fixture(scope="function")
def postgres_dsn(postgres, pytestconfig):
    """ Returns a dsn to a temporary postgres server. Cleans up the database
    after running the tests.

    """
    if pytestconfig.getoption('nopg'):
        yield 'postgresql://postgres:postgres@127.0.0.1:55432/postgres'
        return

    postgres.reset_snapshots()

    yield postgres.url()

    transaction.abort()

    close_all_sessions()
    SessionManager(postgres.url(), None).dispose()

    engine = create_engine(postgres.url())
    results = engine.execute(
        "SELECT DISTINCT table_schema FROM information_schema.tables")

    schemas = set(r['table_schema'] for r in results)

    for schema in schemas:
        if schema.startswith('pg_'):
            continue

        if schema in ('information_schema', 'public'):
            continue

        # having a bad day because your test doesn't work if run with others?
        # did you use a session manager? if yes, make sure to use mgr.dispose()
        # before finishing your test, or use the sesion_manager fixture!
        engine.execute(f'DROP SCHEMA "{schema}" CASCADE')

    # drop all connections
    with suppress(exc.OperationalError):
        engine.execute((
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname='test'"
        ))

    engine.raw_connection().invalidate()
    engine.dispose()

    close_all_sessions()


@pytest.fixture(scope="function")
def session_manager(postgres_dsn):
    """ Provides a :class:`onegov.core.orm.session_manager.SessionManager`
    setup with :func:`postgres_dsn`.

    """

    # in testing we often reuse loaded values after commiting a transaction,
    # so we set expire_on_commit to False. The test applications will still
    # use the default value of True however. This only affects unit tests
    # not working with the app.
    mgr = SessionManager(
        postgres_dsn, Base,
        session_config={
            'expire_on_commit': False
        },
        engine_config={
            'echo': 'ECHO' in os.environ
        }
    )
    yield mgr
    mgr.dispose()


@pytest.fixture(scope="function")
def session(session_manager):
    """ Provides an SQLAlchemy session, scoped to a random schema.

    This is the fixture you usually want to use for ORM tests.

    """

    # the transaction might be in an unclean state at this point
    transaction.abort()

    session_manager.set_current_schema('test_' + uuid4().hex)
    session_manager.set_locale('de_CH', 'de_CH')

    yield session_manager.session()


@pytest.fixture(scope="function")
def temporary_directory():
    """ Provides a temporary directory that is removed after the test. """
    directory = tempfile.mkdtemp()
    yield directory
    shutil.rmtree(directory)


@pytest.fixture(scope="function")
def temporary_path(temporary_directory):
    """ Same as :func:`temporary_directory`, but providing a ``Path`` instead
    of a string. """

    yield Path(temporary_directory)


@pytest.fixture(scope="session")
def es_default_version():
    return '7.5.1'


@pytest.fixture(scope="session")
def es_version(es_default_version):
    return os.environ.get('ES_VERSION', es_default_version)


@pytest.fixture(scope="session")
def es_archive(es_version):
    archive = f'elasticsearch-{es_version}-linux-x86_64.tar.gz'
    archive_path = f'/tmp/{archive}'

    if not os.path.exists(archive_path):
        url = f'https://artifacts.elastic.co/downloads/elasticsearch/{archive}'
        http = urllib3.PoolManager()

        with http.request('GET', url, preload_content=False) as r:
            with open(archive_path, 'wb') as f:
                shutil.copyfileobj(r, f)

    return archive_path


@pytest.fixture(scope="session")
def es_binary(es_archive):
    path = tempfile.mkdtemp()

    try:
        process = subprocess.Popen(
            shlex.split(
                f"tar xzvf {es_archive} -C {path} --strip-components=1"
            ),
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert process.wait() == 0
        yield os.path.join(path, 'bin/elasticsearch')
    finally:
        shutil.rmtree(path)


@pytest.fixture(scope="session")
def es_process(es_binary, es_version):
    port = port_for.select_random()
    pid = es_binary + '.pid'

    # if JAVA_HOME is not defined, try to find it
    if 'JAVA_HOME' not in os.environ:
        os.environ['JAVA_HOME'] = guess_java_home_or_fail()

    # use a different garbage collector for better performance
    os.environ['ES_JAVA_OPTS'] = \
        '-Xms1g -Xmx1g -XX:-UseConcMarkSweepGC -XX:+UseG1GC'

    command = (
        f"{es_binary} -p {pid} -E http.port={port} "
        f"-E xpack.monitoring.enabled=false "
        f"-E xpack.monitoring.collection.enabled=false "
        f"-E xpack.ml.enabled=false "
        f"> /dev/null"
    )

    url = f'http://127.0.0.1:{port}/_cluster/health?wait_for_status=green'

    executor = HTTPExecutor(command, url, method='GET', shell=True)
    executor.start()

    yield executor

    executor.stop()
    executor.kill()


def guess_java_home_or_fail():
    if os.path.exists('/usr/libexec/java_home'):
        result = subprocess.run('/usr/libexec/java_home', capture_output=True)

        if result.returncode != 0:
            raise RuntimeError('/usr/libexec/java_home failed')

        return result.stdout.decode('utf-8').strip()

    raise RuntimeError("Could not find JAVA_HOME, please set it manually")


@pytest.fixture(scope="function")
def es_url(es_process):
    """ Provides an url to an elasticsearch cluster that is guaranteed to be
    empty at the beginning of each test.

    """

    url = es_process.url.geturl()
    url = url.split('/_cluster')[0]

    yield url

    es = Elasticsearch(url)
    es.indices.delete(index='*')
    es.indices.refresh()


@pytest.fixture(scope="function")
def es_client(es_url):
    """ Provides an elasticsearch client. """
    yield Elasticsearch(es_url)


@pytest.fixture(scope="session")
def smtp_server():
    # replacement for smtpserver fixture, which also works on Python 3.5
    # see https://bitbucket.org/pytest-dev/pytest-localserver
    # /issues/13/broken-on-python-35
    from pytest_localserver import smtp

    class Server(smtp.Server):

        def getsockname(self):
            return self.socket.getsockname()

        @property
        def address(self):
            return self.addr[:2]

        def outbox_payloads(self, index):
            return [
                m.get_payload(index).get_payload(decode=True).decode('utf-8')
                for m in self.outbox
            ]

        @property
        def sent(self):
            """ Similar to the outbox property, this property returns the
            sent e-mails, but only the decoded plaintext format.

            """
            return self.outbox_payloads(0)

        @property
        def sent_html(self):
            """ Similar to the outbox property, this property returns the
            sent e-mails, but only the decoded html format.

            """
            return self.outbox_payloads(1)

    server = Server()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="function")
def smtp(smtp_server):
    yield smtp_server
    del smtp_server.outbox[:]


@pytest.fixture(scope="session")
def memcached_server():
    path = shutil.which('memcached')

    if not path:
        raise RuntimeError("Could not find memcached executable")

    host = '127.0.0.1'
    port = port_for.select_random()

    executor = TCPExecutor(f'memcached -l {host} -p {port}', host, port)
    executor.start()

    yield executor

    executor.stop()
    executor.kill()


@pytest.fixture(scope="function")
def memcached_url(memcached_server):
    host, port = memcached_server.host, memcached_server.port

    yield f'{host}:{port}'

    os.system(f"echo 'flush_all' | nc {host} {port} > /dev/null")


@pytest.fixture(scope="session")
def test_password():
    return hash_password('hunter2')


@pytest.fixture(scope="session")
def long_lived_filestorage():
    return TempFS()


@pytest.fixture(scope="session")
def webdriver():
    return 'chrome'


@pytest.fixture(scope="session")
def webdriver_options():
    options = Options()
    options.add_argument('--no-sandbox')

    if os.environ.get('SHOW_BROWSER') != '1':
        options.add_argument('--headless')

    return options


@pytest.fixture(scope="session")
def webdriver_executable_path():
    pattern = r'\d+\.\d+\.\d+'
    stdout = os.popen(
        'google-chrome --version || google-chrome-stable --version'
    ).read()
    version = re.search(pattern, stdout)
    if version:
        driver = ChromeType.GOOGLE
    else:
        driver = ChromeType.CHROMIUM
    return ChromeDriverManager(chrome_type=driver).install()


@pytest.fixture(scope="session")
def browser_extension():
    return ExtendedBrowser


@pytest.fixture(scope="function")
def browser(webdriver, webdriver_options, webdriver_executable_path,
            browser_extension):

    config = {
        'executable_path': webdriver_executable_path,
        'options': webdriver_options,

        # preselect a port as selenium picks it in a way that triggers the
        # macos firewall to display a confirmation dialog
        'port': port_for.select_random()
    }

    with browser_extension.spawn(Browser, webdriver, **config) as browser:
        yield browser


@pytest.fixture(scope="function")
def redis_url(redis_server):
    url = f'redis://{redis_server.host}:{redis_server.port}/0'
    yield url

    Redis.from_url(url).flushall()


@pytest.fixture(scope="session")
def glauth_binary():
    v = '1.1.1'
    n = platform.system() == 'Darwin' and 'glauthOSX' or 'glauth64'
    url = f'https://github.com/glauth/glauth/releases/download/v{v}/{n}'

    path = '/tmp/glauth'

    if not os.path.exists(path):
        http = urllib3.PoolManager()

        with http.request('GET', url, preload_content=False) as r:
            assert r.status == 200, "Can't get glauth binary"
            with open(path, 'wb') as f:
                shutil.copyfileobj(r, f)

        os.chmod('/tmp/glauth', 0o755)

    # short check if binary is downloaded correctly
    assert os.path.getsize(path) > 6000000

    return path
