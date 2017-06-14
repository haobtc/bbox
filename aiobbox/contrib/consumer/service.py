import time
import re
import uuid
from hashlib import sha256
from aiobbox.server import Service
from aiobbox.exceptions import ServiceError
from aiobbox.cluster import get_sharedconfig
from aiobbox.utils import parse_int

srv = Service()

@srv.method('createConsumerToken')
async def create_consumer_token(request, consumer, secret, options=None):
    if options is None:
        options = {} #'expire_in': 3 * 86400}

    cfg = get_sharedconfig()
    coptions = cfg.get('consumers', consumer)
    if not coptions:
        raise ServiceError('consumer not found')

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
        'token': token,
        'expire_at': expire_at
    }

@srv.method('verifyConsumerToken')
async def verify_consumer_token(request, token):
    arr = token.split('|')
    if len(arr) != 4 or re.search(r'\s', token):
        raise ServiceError('invalid token')

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
    
