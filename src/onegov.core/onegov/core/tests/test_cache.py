from onegov.core import Framework
from morepath import setup
from webtest import TestApp as Client


CALL_COUNT = 0


def test_cache():
    config = setup()

    class App(Framework):
        testing_config = config

    @App.path(path='/')
    class Root(object):
        pass

    @App.html(model=Root)
    def view_root(self, request):
        @request.app.cache.cache_on_arguments()
        def call_count():
            global CALL_COUNT
            CALL_COUNT += 1
            return str(CALL_COUNT)

        return call_count()

    config.commit()

    app = App()
    app.namespace = 'towns'
    app.configure_application(memcached_connections=2)
    app.cache_backend = 'dogpile.cache.memory'
    app.cache_backend_arguments = {}

    client = Client(app)

    # with a limit of two connections we'll see that whenever a third
    # applicaiton is used, the last used application is lost
    #
    # we won't necessarily see this with memcached - memcached does it's own
    # lru and we don't try to influence that - here we lose the cache because
    # if we use a memory cache backend we lose the cache when discarding
    # the backend
    app.set_application_id('towns/washington')
    assert client.get('/').text == '1'
    assert client.get('/').text == '1'

    app.set_application_id('towns/arlington')
    assert client.get('/').text == '2'
    assert client.get('/').text == '2'

    app.set_application_id('towns/washington')
    assert client.get('/').text == '1'

    app.set_application_id('towns/detroit')
    assert client.get('/').text == '3'

    app.set_application_id('towns/washington')
    assert client.get('/').text == '1'

    app.set_application_id('towns/detroit')
    assert client.get('/').text == '3'

    app.set_application_id('towns/arlington')
    assert client.get('/').text == '4'
