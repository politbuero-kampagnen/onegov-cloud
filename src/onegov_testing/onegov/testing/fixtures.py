import pytest
import tempfile
import shutil

from onegov.core.orm import Base, SessionManager
from sqlalchemy import create_engine
from testing.postgresql import Postgresql
from uuid import uuid4


@pytest.yield_fixture(scope="session")
def postgres():
    """ Starts a postgres server using `testing.postgresql \
    <https://pypi.python.org/pypi/testing.postgresql/`_ once per test session.

    """

    postgres = Postgresql()
    yield postgres
    postgres.stop()


@pytest.yield_fixture(scope="function")
def postgres_dsn(postgres):
    """ Returns a dsn to a temporary postgres server. Cleans up the database
    after running the tests.

    """
    yield postgres.url()

    engine = create_engine(postgres.url())
    results = engine.execute(
        "SELECT DISTINCT table_schema FROM information_schema.tables")

    schemas = set(r['table_schema'] for r in results)

    for schema in schemas:
        if schema.startswith('pg_'):
            continue

        if schema in ('information_schema', 'public'):
            continue

        engine.execute('DROP SCHEMA "{}" CASCADE'.format(schema))

    engine.raw_connection().invalidate()
    engine.dispose()


@pytest.yield_fixture(scope="function")
def session_manager(postgres_dsn):
    """ Provides a :class:`onegov.core.orm.session_manager.SessionManager`
    setup with :func:`postgres_dsn`.

    """

    mgr = SessionManager(postgres_dsn, Base)
    yield mgr
    mgr.dispose()


@pytest.yield_fixture(scope="function")
def session(postgres_dsn):
    """ Provides an SQLAlchemy session, scoped to a random schema.

    This is the fixture you usually want to use for ORM tests.

    """
    session_manager.set_current_schema('test_' + uuid4().hex)
    yield session_manager.session()


@pytest.yield_fixture(scope="function")
def temporary_directory():
    """ Provides a temporary directory that is removed after the test. """
    directory = tempfile.mkdtemp()
    yield directory
    shutil.rmtree(directory)
