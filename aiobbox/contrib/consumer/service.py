import time
import ssl
import re
import uuid
from hashlib import sha256
from aiobbox import testing
from aiobbox.server import Service
from aiobbox.cluster import get_cluster
from aiobbox.exceptions import ServiceError
from aiobbox.cluster import get_sharedconfig

srv = Service()
srv.__doc__ = '''
Consumer service provides consumer token generation and verification.
It is composed since many other services need similiar funcs.
'''
@srv.method('createConsumer')
async def create_consumer(request, consumer, reuse):
    '''
    createConsumer(consumer, reuse)
    create a consumer for test, note that this methods is *ONLY* used for testing. Production consumer can be created using `bbox.py run aiobbox.contrib.consumer.create_consumer <name>`
    '''
    cfg = get_sharedconfig()

    allow_create_consumer = cfg.get('consumers', 'allow_create')
    if not testing.test_mode() and not allow_create_consumer:
        raise ServiceError('access denied')

    if (not isinstance(consumer, str)
        or not re.match(r'\w+$', consumer)):
        raise ServiceError('invalid consumer')


    coptions = cfg.get('consumers', consumer)
    #if coptions:
    #    raise ServiceError('consumer already exist',
    #                       msg='already exist {}'.format(coptions))
    if coptions and reuse:
        return {
            'consumer': consumer,
            'secret': coptions['secret']
        }

    coptions = {}
    coptions['secret'] = uuid.uuid4().hex
    coptions['seed'] = ssl.RAND_bytes(256).hex()

    c = get_cluster()
    if c.use_local_configs():
        await c.set_config('consumers', consumer, coptions)

    # TODO: limit the consumer size
    return {
        'consumer': consumer,
        'secret': coptions['secret']
    }

@srv.method('createToken')
async def create_consumer_token(request, consumer, secret, options=None):
    '''
    createToken(consumer, secret, options=None)
    Create a consume token by preallocated consumer and secret
    '''

    if not isinstance(consumer, str):
        raise ServiceError('invalid consumer')
    options = options or {}
    cfg = get_sharedconfig()
    coptions = cfg.get('consumers', consumer)
    if not coptions:
        raise ServiceError('consumer not found')

    if not isinstance(secret, str):
        raise ServiceError('invalid secret')

    if coptions['secret'] != secret:
        raise ServiceError('consumer verify failed')

    expire_in = int(options.get('expire_in', 3 * 365 * 86400))
    if expire_in < 60:
        raise ServiceError('cannot expire too early')

    expire_at = int(time.time() + expire_in)
    nonce = uuid.uuid4().hex
    digest_src = ':'.join([
        consumer, str(expire_at),
        nonce, coptions['seed']])
    m = sha256()
    m.update(digest_src.encode('utf-8'))
    digest = m.hexdigest()
    token = ':'.join([consumer,
                      str(expire_at),
                      nonce, digest])
    return {
        'consumer': consumer,
        'token': token,
        'expire_at': expire_at
    }

@srv.method('verifyToken')
async def verify_consumer_token(request, token):
    '''
    verifyToken(token)
    verify a token, it may be invalid or expired
    '''
    arr = token.split(':')
    if len(arr) != 4 or re.search(r'\s', token):
        raise ServiceError('invalid token',
                           'token {}'.format(token))

    consumer, expire_at, nonce, digest = arr
    cfg = get_sharedconfig()
    coptions = cfg.get('consumers', consumer)
    if not coptions:
        raise ServiceError('consumer not found')

    if int(expire_at) < time.time():
        raise ServiceError('token expired')

    digest_src = ':'.join([
        consumer, expire_at,
        nonce, coptions['seed']])
    m = sha256()
    m.update(digest_src.encode('utf-8'))
    new_digest = m.hexdigest()
    if new_digest != digest:
        raise ServiceError('verify failed')

    return {
        'consumer': consumer,
        'expire_at': expire_at,
        'verified': True
        }

srv.register('bbox.consumer')
