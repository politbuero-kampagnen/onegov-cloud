import certifi
import morepath
import ssl

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from elasticsearch import ConnectionError  # shadows a python builtin!
from elasticsearch import Elasticsearch
from elasticsearch import Transport
from elasticsearch import TransportError
from elasticsearch.connection import create_ssl_context
from more.transaction.main import transaction_tween_factory
from onegov.search import Search, log
from onegov.search.errors import SearchOfflineError
from onegov.search.indexer import Indexer
from onegov.search.indexer import ORMEventTranslator
from onegov.search.indexer import TypeMappingRegistry
from onegov.search.utils import searchable_sqlalchemy_models
from sortedcontainers import SortedSet
from sqlalchemy import inspect
from sqlalchemy.orm import undefer
from urllib3.exceptions import HTTPError


class TolerantTransport(Transport):
    """ A transport class that is less eager to rejoin connections when there's
    a failure. Additionally logs all Elasticsearch transport errors in one
    location.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failure_time = None
        self.failures = 0

    @property
    def skip_request(self):
        """ Returns True if the request should be skipped. """

        if not self.failures:
            return False

        if not self.seconds_remaining:
            return False

        return True

    @property
    def seconds_remaining(self):
        """ Returns the seconds remaining until the next try or 0.

        For each failure we wait an additional 10s (10s, then 20s, 30s, etc),
        up to a maximum of 300s (5 minutes).
        """

        timeout = min((self.failures * 10), 300)
        elapsed = (datetime.utcnow() - self.failure_time).total_seconds()

        return int(max(timeout - elapsed, 0))

    def perform_request(self, *args, **kwargs):
        if self.skip_request:
            log.info(f"Elasticsearch down, retry in {self.seconds_remaining}s")
            raise SearchOfflineError()

        try:
            response = super().perform_request(*args, **kwargs)
        except (TransportError, HTTPError) as e:
            # transport errors might be caused by bugs (for example, when we
            # refer to a non-existant index) -> we are only tolerant of
            # connection errors
            if isinstance(e, TransportError):
                if not isinstance(e, ConnectionError):
                    if not is_5xx_error(e):
                        raise

            self.failures += 1
            self.failure_time = datetime.utcnow()

            log.exception("Elasticsearch cluster is offline")
            raise SearchOfflineError()

        else:
            self.failures = 0
            return response


def is_5xx_error(error):
    return error.status_code and str(error.status_code).startswith('5')


class ElasticsearchApp(morepath.App):
    """ Provides elasticsearch integration for
    :class:`onegov.core.framework.Framework` based applications.

    The application must be connected to a database.

    Usage::

        from onegov.core import Framework

        class MyApp(Framework, ESIntegration):
            pass

    """

    def configure_search(self, **cfg):
        """ Configures the elasticsearch client, leaving it as a property
        on the class::

            app.es_client

        The following configuration options are accepted:

        :enable_elasticsearch:
            If True, elasticsearch is enabled (defaults to True).

        :elasticsearch_hosts:
            A list of elasticsearch clusters, including username, password,
            protocol and port.

            For example: ``https://user:secret@localhost:443``

            By default the client connects to the localhost on port 9200
            (the default), and on port 19200 (the default of boxen).

            At least one host in the list of servers must be up at startup.

        :elasticsearch_may_queue_size:
            The maximum queue size reserved for documents to be indexed. This
            queue is filling up if the elasticsearch cluster cannot be reached.

            Once the queue is full, warnings are emitted.

            Defaults to 10'000

        :elasticsearch_verify_certs:
            If true, the elasticsearch client verifies the certificates of
            the ssl connection. Defaults to true. Do not disable, unless you
            are in testing!

        :elasticsearch_languages:
            The languages supported by onegov.search. Defaults to:
                - en
                - de
                - fr
        """

        if not cfg.get('enable_elasticsearch', True):
            self.es_client = None
            return

        self.es_hosts = cfg.get('elasticsearch_hosts', (
            'http://localhost:9200',
        ))

        self.es_verify_certs = cfg.get('elasticsearch_verify_certs', True)

        if cfg.get('elasticsearch_verify_certs', True):
            self.es_extra_params = {
                'verify_certs': True,
                'ca_certs': certifi.where()
            }
        else:
            ssl_context = create_ssl_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.es_extra_params = {
                'verify_certs': False,
                'ssl_context': ssl_context
            }

        self.es_configure_client(usage='default')

        if self.has_database_connection:
            max_queue_size = int(cfg.get(
                'elasticsarch_max_queue_size', '10000'))

            self.es_mappings = TypeMappingRegistry()

            for base in self.session_manager.bases:
                self.es_mappings.register_orm_base(base)

            self.es_orm_events = ORMEventTranslator(
                self.es_mappings,
                max_queue_size=max_queue_size
            )

            self.es_indexer = Indexer(
                self.es_mappings,
                self.es_orm_events.queue,
                es_client=self.es_client
            )

            self.session_manager.on_insert.connect(
                self.es_orm_events.on_insert)
            self.session_manager.on_update.connect(
                self.es_orm_events.on_update)
            self.session_manager.on_delete.connect(
                self.es_orm_events.on_delete)

    def es_configure_client(self, usage='default'):
        usages = {
            'default': {
                'timeout': 3,
                'max_retries': 1
            },
            'reindex': {
                'timeout': 10,
                'max_retries': 3
            }
        }

        self.es_client = Elasticsearch(
            hosts=self.es_hosts,
            transport_class=TolerantTransport,
            **usages[usage],
            **self.es_extra_params
        )

    def es_search(self, languages='*', types='*', include_private=False,
                  explain=False):
        """ Returns a search scoped to the current application, with the
        given languages, types and private documents excluded by default.

        """

        search = Search(
            session=self.session(),
            mappings=self.es_mappings,
            using=self.es_client,
            index=self.es_indices(languages, types),
            extra=dict(explain=explain)
        )

        if not include_private:
            search = search.filter("term", es_public=True)

        # by default, do not include any fields (this will still include
        # the id and the type, which is enough for the orm querying)
        search = search.source(excludes=['*'])

        return search

    def es_indices(self, languages='*', types='*'):
        return self.es_indexer.ixmgr.get_external_index_names(
            schema=self.schema,
            languages=languages,
            types=types
        )

    def es_search_by_request(self, request, types='*', explain=False,
                             limit_to_request_language=False):
        """ Takes the current :class:`~onegov.core.request.CoreRequest` and
        returns an elastic search scoped to the current application, the
        requests language and it's access rights.

        """

        if limit_to_request_language:
            languages = [request.locale.split('_')[0]]
        else:
            languages = '*'

        return self.es_search(
            languages=languages,
            types=types,
            include_private=self.es_may_use_private_search(request),
            explain=explain
        )

    def es_suggestions(self, query, languages='*', types='*',
                       include_private=False):
        """ Returns suggestions for the given query. """

        if not query:
            return []

        if include_private:
            context = ['public', 'private']
        else:
            context = ['public']

        search = self.es_search(
            languages=languages,
            types=types,
            include_private=include_private
        )

        search = search.suggest(
            name='es_suggestion',
            text=query,
            completion={
                'field': 'es_suggestion',
                'skip_duplicates': True,
                'contexts': {
                    'es_suggestion_context': context
                }
            }
        )

        result = search.execute()

        # if there's no matching index, no suggestions are returned, which
        # happens if the Elasticsearch cluster is being rebuilt
        if not hasattr(result, 'suggest'):
            return ()

        suggestions = SortedSet()

        for suggestion in getattr(result.suggest, 'es_suggestion', []):
            for item in suggestion['options']:
                suggestions.add(item['text'].strip())

        return tuple(suggestions)

    def es_suggestions_by_request(self, request, query, types='*',
                                  limit_to_request_language=False):
        """ Returns suggestions for the given query, scoped to the language
        and the login status of the given requst.

        """
        if limit_to_request_language:
            languages = [request.locale.split('_')[0]]
        else:
            languages = '*'

        return self.es_suggestions(
            query,
            languages=languages,
            types=types,
            include_private=self.es_may_use_private_search(request)
        )

    def es_may_use_private_search(self, request):
        """ Returns True if the given request is allowed to access private
        search results. By default every logged in user has access to those.

        This method may be overwritten if this is not desired.

        """
        return request.is_logged_in

    def es_perform_reindex(self, fail=False):
        """ Reindexes all content.

        This is a heavy operation and should be run with consideration.

        By default, all exceptions during reindex are silently ignored.

        """

        self.es_configure_client(usage='reindex')
        self.es_indexer.ixmgr.created_indices = set()

        # delete all existing indices for this town
        ixs = self.es_indexer.ixmgr.get_managed_indices_wildcard(self.schema)
        self.es_client.indices.delete(ixs)

        # have no queue limit for reindexing (that we're able to change
        # this here is a bit of a CPython implementation detail) - we can't
        # necessarily always rely on being able to change this property
        self.es_orm_events.queue.maxsize = 0

        # load all database objects and index them
        def reindex_model(model):
            session = self.session()

            try:
                q = session.query(model).options(undefer('*'))
                i = inspect(model)

                if i.polymorphic_on is not None:
                    q = q.filter(i.polymorphic_on == i.polymorphic_identity)

                for obj in q:
                    self.es_orm_events.index(self.schema, obj)
            finally:
                session.invalidate()
                session.bind.dispose()

        # by loading models in threads we can speed up the whole process
        with ThreadPoolExecutor() as executor:
            results = executor.map(
                reindex_model, (
                    model
                    for base in self.session_manager.bases
                    for model in searchable_sqlalchemy_models(base)
                )
            )
            if fail:
                tuple(results)

        self.es_indexer.bulk_process()


@ElasticsearchApp.tween_factory(over=transaction_tween_factory)
def process_indexer_tween_factory(app, handler):
    def process_indexer_tween(request):

        if not request.app.es_client:
            return handler(request)

        result = handler(request)
        request.app.es_indexer.process()
        return result

    return process_indexer_tween
