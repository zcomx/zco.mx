"""
Example of usage:

cache.memcache = MemcacheClient(request, [127.0.0.1:11211], debug=true)
"""
import _thread
import pickle
import time
from applications.zcomx.modules.memcache.memcache import Client
from gluon.cache import CacheAbstract
from gluon import current

DEFAULT_TIME_EXPIRE = 300     # seconds (must be the same as cache.ram)


def MemcacheClient(*a, **b):
    """Memcache client."""
    # pylint: disable=protected-access
    # pylint: disable=invalid-name
    if not hasattr(current, '__memcache_client'):
        current.__memcache_client = MemcacheClientObj(*a, **b)
    return current.__memcache_client


class MemcacheClientObj(Client):
    """Client with memcache."""

    def initialize(self):
        """Initialize client."""

    meta_storage = {}
    max_time_expire = 24 * 3600

    def __init__(self, request, servers, debug=0, pickleProtocol=0,
                 pickler=pickle.Pickler, unpickler=pickle.Unpickler,
                 pload=None, pid=None,
                 default_time_expire=DEFAULT_TIME_EXPIRE):
        self.request = request
        self.default_time_expire = default_time_expire
        if request:
            app = request.application
        else:
            app = ''
        Client.__init__(self, servers, debug, pickleProtocol,
                        pickler, unpickler, pload, pid)
        if app not in self.meta_storage:
            self.storage = self.meta_storage[app] = {
                CacheAbstract.cache_stats_name: {
                    'hit_total': 0,
                    'misses': 0,
                }
            }
        else:
            self.storage = self.meta_storage[app]

    def __call__(self, key, f, time_expire='default'):
        if time_expire == 'default':
            time_expire = self.default_time_expire
        if time_expire == None:
            time_expire = self.max_time_expire
        # this must be commented because get and set are redefined
        # key = self.__keyFormat__(key)
        now = time.time()
        value = None
        if f is None:     # force deletion of value
            self.delete(key)
            return None
        if time_expire == 0:     # value forced expired
            item = None     # value to be computed
        else:
            item = self.get(key)
            if item:
                if not isinstance(item, (list, tuple)):
                    value = item
                elif item[0] < (now - time_expire):
                    # value has expired, set to None so it is computed
                    item = None
                else:
                    value = item[1]
        if not item:
            value = f()
            self.set(key, (now, value), self.max_time_expire)
        return value

    def increment(self, key, value=1, time_expire='default'):
        """ time_expire is ignored """
        if time_expire == 'default':
            time_expire = self.default_time_expire
        new_key = self.__keyFormat__(key)
        obj = Client.get(self, new_key)
        if obj:
            if isinstance(obj, (int, float)):
                return Client.incr(self, new_key, value)
            value += obj[1]
            Client.set(self, new_key, (time.time(), value),
                       self.max_time_expire)
            return value
        Client.set(self, new_key, value, self.max_time_expire)
        return value

    def set(self, key, value, time_expire='default'):
        # pylint: disable=arguments-differ
        if time_expire == 'default':
            time_expire = self.default_time_expire
        new_key = self.__keyFormat__(key)
        return Client.set(self, new_key, value, time_expire)

    def get(self, key):
        new_key = self.__keyFormat__(key)
        return Client.get(self, new_key)

    def delete(self, key):
        # pylint: disable=arguments-differ
        new_key = self.__keyFormat__(key)
        return Client.delete(self, new_key)

    def __keyFormat__(self, key):
        # pylint: disable=invalid-name
        return '%s/%s' % (self.request.application, key.replace(' ', '_'))
