""" Provides a simple and mostly transparent way of defining orm-cached
properties on the application class.

For example::

    from onegov.core import Framework
    from onegov.core.orm import orm_cached

    class App(Framework):

        @orm_cached(policy='on-table-change:users')
        def users(self):
            # ... fetch users from database

Properties defined in this way are accessible through the instance::

    app.users

If there are any changes to the users table, the cache is removed. Since the
cache is usually a shared memcached instance, this works for multiple
processes.

"""

import inspect
import sqlalchemy

from sqlalchemy.orm.query import Query


class OrmCacheApp(object):
    """ Integrates the orm cache handling into the application
    (i.e. :class:`onegov.core.framework.Framework').

    In addition, the application needs to call :meth:`setup_orm_cache` inside
    of `:meth:onegov.server.application.Application.set_application_id` to
    enable the cache evicition mechanism.

    """

    def configure_orm_cache(self, **cfg):
        self.is_orm_cache_setup = getattr(self, 'is_orm_cache_setup', False)

    def setup_orm_cache(self):
        """ Sets up the event handlers for the change-detection. """

        assert not self.is_orm_cache_setup

        for descriptor in self.orm_cache_descriptors:
            self.session_manager.on_insert.connect(
                self.descriptor_bound_orm_change_handler(descriptor),
                weak=False)
            self.session_manager.on_update.connect(
                self.descriptor_bound_orm_change_handler(descriptor),
                weak=False)
            self.session_manager.on_delete.connect(
                self.descriptor_bound_orm_change_handler(descriptor),
                weak=False)

        self.is_orm_cache_setup = True

    def descriptor_bound_orm_change_handler(self, descriptor):
        """ Listens to changes to the database and evicts the cache if the
        policy demands it. Available policies:

        * policy='on-table-change:table': clears the cache if there's a change
          on the given table

        * policy=lambda obj: ...: clears the cache if the given policy function
          returns true (it receives the object which has changed)

        """

        def handle_orm_change(schema, obj):

            if callable(descriptor.cache_policy):
                dirty = descriptor.cache_policy(obj)

            elif descriptor.cache_policy.startswith('on-table-change'):
                tablename = descriptor.cache_policy.split(':')[-1]
                dirty = obj.__class__.__tablename__ == tablename

            else:
                raise NotImplementedError()

            if dirty:
                # Two circumstances ensure that only the cache of the current
                # schema is evicted:
                #
                # 1. There's a current schema set when the event is fired.
                # 2. The current cache is bound to the current schema.
                #
                # Still, trust but verify:
                assert self.schema == schema
                self.cache.delete(descriptor.cache_key)

                if descriptor.cache_key in self.request_cache:
                    del self.request_cache[descriptor.cache_key]

        return handle_orm_change

    @property
    def orm_cache_descriptors(self):
        """ Yields all orm cache descriptors installed on the class. """

        for member_name, member in inspect.getmembers(self.__class__):
            if isinstance(member, OrmCacheDescriptor):
                yield member


class OrmCacheDescriptor(object):
    """ The descriptor implements the protocol for fetching the objects
    either from cache or from the database (through the handler).

    """

    def __init__(self, cache_policy, creator):
        self.cache_policy = cache_policy
        self.cache_key = creator.__qualname__
        self.creator = creator

    def create(self, instance):
        """ Uses the creator to load the object to be cached.

        Since the return value of the creator might not be something we want
        to cache, this function will turn some return values into something
        more useful (e.g. queries are completely fetched).

        """
        result = self.creator(instance)

        if isinstance(result, Query):
            result = tuple(result)

        return result

    def merge(self, session, obj):
        """ Merges the given obj into the given session, *if* this is possible.

        That is it acts like more forgiving session.merge().

        """

        # the records we merge back from the pickled state aren't always
        # properly flushed if we they are marged into other queries, so
        # before merging we must be sure that all state has been flushed
        if session.dirty:
            session.flush()

        if sqlalchemy.inspect(obj, raiseerr=False):
            obj = session.merge(obj, load=False)
            obj.is_cached = True
        return obj

    def __get__(self, instance, owner):
        """ Handles the object/cache access. """

        if instance is None:
            return self

        # we use a secondary request cache for even more lookup speed and to
        # make sure that inside a request we always get the exact same instance
        # (otherwise we don't see changes reflected)
        if self.cache_key in instance.request_cache:
            return instance.request_cache[self.cache_key]

        obj = instance.cache.get_or_create(
            key=self.cache_key,
            creator=lambda: self.create(instance)
        )

        session = instance.session()

        # named tuples
        if isinstance(obj, tuple) and hasattr(obj.__class__, '_make'):
            obj = obj._make(self.merge(session, o) for o in obj)

        # lists (we can save some memory here)
        elif isinstance(obj, list):
            for ix, o in enumerate(obj):
                obj[ix] = self.merge(session, o)

        # generic iterables
        elif isinstance(obj, (tuple, set)):
            obj = obj.__class__(self.merge(session, o) for o in obj)

        # generic objects
        else:
            obj = self.merge(session, obj)

        instance.request_cache[self.cache_key] = obj

        return obj


def orm_cached(policy):
    """ The decorator use to setup the cache descriptor.

    See the :module:`onegov.core.orm.cache` docs for usage.

    """

    def orm_cache_decorator(fn):
        return OrmCacheDescriptor(policy, fn)
    return orm_cache_decorator
