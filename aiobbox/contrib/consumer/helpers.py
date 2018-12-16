from aiobbox.cluster import get_sharedconfig

def has_consumer(consumer):
    cfg = get_sharedconfig()
    return cfg.has_key('consumers', consumer)
