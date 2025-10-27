from django.core.cache import cache

def get_cached_data(key):
    """
        Retrieve data from cache if available.
        Returns None if not found.
    """

    return cache.get(key)


def set_cached_data(key, data, timeout):
    """
        Store data in cache for a specific duration (in seconds).
    """

    cache.set(key, data, timeout)


def delete_cache_key(key):
    """
        Manually clear a cached item by its key.
    """

    cache.delete(key)


def get_or_set_cache(key, fetch_function, timeout):
    """
        Common pattern: returns cached data if exists,
        else runs fetch_function(), caches the result, and returns it.
    """
    
    data = cache.get(key)
    if not data:
        data = fetch_function()
        cache.set(key, data, timeout)
    return data
