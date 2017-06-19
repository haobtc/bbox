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
from aiobbox.utils import parse_int

srv = Service()

@srv.method('createConsumer')
async def create_consumer(request, consumer):
    '''
    Create a consumer for test
    -----
    parameters:
      - name: consumer
        description: consumer name
        type: string
        require: true

    return:
      - name: consumer
        description: the same name with the parameter
        type: string

      - name: secret
        description: consumer secret used to get consumer token
        type: string
    '''
    if not testing.test_mode:
        raise ServiceError('access denied')

    if (not isinstance(consumer, str)
        or not re.match(r'\w+$', consumer)):
        raise ServiceError('invalid consumer')

    cfg = get_sharedconfig()
    coptions = cfg.get('consumers', consumer)
    if coptions:
        raise ServiceError('consumer already exist')

    coptions = {}
    coptions['secret'] = uuid.uuid4().hex
    coptions['seed'] = ssl.RAND_bytes(256).hex()

    c = get_cluster()
    await c.set_config('consumers', consumer, coptions)

    # TODO: limit the consumer size
    return {
        'consumer': consumer,
        'secret': coptions['secret']
    }

@srv.method('createToken')
async def create_consumer_token(request, consumer, secret, options=None):
    '''
    Create a consume token by secret
    -----
    parameters:
      - name: consumer
        description: the consumer name
        type: string
        require: true
      - name: secret
        description: consumer secret
        type: string
        require: true
      - name options
        descriptions: consumer token options
        type: string
        require: true
        elements:
          - name: expire_in
            description: the consumer token expiration in seconds
            type: int
            require: false
            default: 3 * 86400
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

    expire_in = int(options.get('expire_in', 3 * 86400))
    if expire_in < 60:
        raise ServiceError('cannot expire too early')

    expire_at = int(time.time() + expire_in)
    nonce = uuid.uuid4().hex
    digest_src = '|'.join([
        consumer, str(expire_at),
        nonce, coptions['seed']])
    m = sha256()
    m.update(digest_src.encode('utf-8'))
    digest = m.hexdigest()
    token = '|'.join([consumer,
                      str(expire_at),
                      nonce, digest])
    return {
        'consumer': consumer,
        'token': token,
        'expire_at': expire_at
    }

@srv.method('verifyToken')
async def verify_consumer_token(request, token):
    arr = token.split('|')
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

    digest_src = '|'.join([
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

