from typing import Dict, Any, List, Union, Iterable, Optional
import logging
import time
import sys, os
import asyncio
import random
import aiohttp
from urllib.parse import urljoin
import json
from aiohttp import ClientConnectorError
from aiobbox.cluster import get_cluster
from aiobbox.exceptions import ConnectionError, Retry, NoServiceFound
from aiobbox.utils import  get_cert_ssl_context, next_request_id

from aiobbox.jsonrpc import Request
from aiobbox.server import has_service, ServiceRequest

logger = logging.getLogger('bbox')

DEFAULT_TIMEOUT_SECS = 10

class HttpClient:
    session: Optional[aiohttp.ClientSession]

    def __init__(self, connect: str, expect: str='text') -> None:
        self.expect = expect
        c = get_cluster()
        box = c.boxes[connect]
        self.ssl_prefix = box['ssl']
        if self.ssl_prefix:
            self.url_prefix = 'https://' + connect
        else:
            self.url_prefix = 'http://' + connect
        ssl_context = get_cert_ssl_context(self.ssl_prefix)
        conn = aiohttp.TCPConnector(ssl_context=ssl_context)
        self.session = aiohttp.ClientSession(connector=conn)

    async def request(self, srv: str, method: str, *params: Any, req_id:Any=None, timeout: float=DEFAULT_TIMEOUT_SECS) -> Any:
        '''
        self.request() is an outdated method, use self.request_obj instead
        '''
        if req_id is None:
            req_id = next_request_id()
        req = Request.make(req_id, srv, method, *params)
        return await self.request_obj(req, timeout=timeout)

    async def request_obj(self, req: Request, timeout:float =DEFAULT_TIMEOUT_SECS) -> Any:
        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')
        payload = req.as_json()
        headers = {'X-Bbox-Expect-Timeout': str(timeout)}
        req_start_time = time.time()
        try:
            for i in range(2):
                try:
                    assert self.session is not None
                    async with self.session.post(
                            url,
                            headers=headers,
                            json=payload,
                            timeout=timeout) as resp:
                        if self.expect == 'text':
                            return await resp.text()
                        else:
                            return await resp.json()
                except ClientConnectorError:
                    logging.warn("connect json rpc error %s, try refresh get_boxes and call again", url)
                    await get_cluster().get_boxes()
                    if i >= 1:
                        raise
        finally:
            used_time = time.time() - req_start_time
            if used_time > 2.0:
                logging.warn(
                    'long bbox request, '
                    'url %s, payload %s, used %s seconds',
                    url, payload, used_time)

    def __del__(self) -> None:
        self.session = None

class ServiceRef:
    def __init__(self, srv_name: str, pool: 'ServicePool') -> None:
        self.name:str = srv_name
        self.pool:ServicePool = pool

    def __getattr__(self, name: str) -> Any:
        return MethodRef(name, self)

class MethodRef:
    def __init__(self, name: str, srv_ref: ServiceRef) -> None:
        self.name = name
        self.srv_ref = srv_ref

    async def __call__(self, *params:Any, **kw:Any) -> Any:
        return await self.srv_ref.pool.request(
            self.srv_ref.name,
            self.name,
            *params,
            **kw)

class ServicePool:
    async def request(self, srv_name: str, method: str, *params:Any, boxid: str=None, retry: int=0, req_id: Any=None, timeout: float=DEFAULT_TIMEOUT_SECS):
        raise NotImplementedError

class SimpleHttpPool(ServicePool):
    ''' short term HTTP request '''
    FIRST = 1
    RANDOM = 2

    def __init__(self) -> None:
        self.pool: Dict[str, ServiceRef] = {}
        self.policy: int = self.RANDOM

    def get_client(self, srv_name: str, policy: int=None, boxid: str=None):
        policy = policy or self.policy
        connects = []
        cc = get_cluster()
        for bind in cc.route[srv_name]:
            if boxid:
                box = cc.boxes.get(bind)
                if box.boxid != boxid:
                    continue
            if policy == self.FIRST:
                connects.append(bind)
                break
            else:
                assert policy == self.RANDOM
                connects.append(bind)

        if connects:
            connect = random.choice(connects)
            return HttpClient(connect, expect='json')

    def __getattr__(self, name: str) -> ServiceRef:
        return ServiceRef(name, self)

    def __getitem__(self, name: str) -> ServiceRef:
        return ServiceRef(name, self)

    async def request(self, srv_name: str, method: str, *params:Any, boxid: str=None, retry: int=0, req_id: Any=None, timeout: float=DEFAULT_TIMEOUT_SECS):
        if not req_id:
            req_id = next_request_id()
        req = Request.make(req_id, srv_name, method, *params)
        return await self.request_obj(req, timeout=timeout, retry=retry)

    async def request_obj(self, req, timeout=DEFAULT_TIMEOUT_SECS, retry=0) -> Any:
        if has_service(req.srv_name):
            # if local has srv_name,
            # call it by default to avoid network failure
            #sreq = ServiceRequest.from_req(req)
            sreq = ServiceRequest(req)
            return await sreq.handle()

        for rty in range(retry + 1):
            try:
                return await self._request_obj(
                    req,
                    boxid=None,
                    timeout=timeout)
            except Retry:
                continue
        raise ConnectionError(
            'cannot retry connections')

    async def _request_obj(self, req, boxid=None, timeout=DEFAULT_TIMEOUT_SECS) -> Any:
        client = self.get_client(req.srv_name, boxid=boxid)
        if not client:
            raise NoServiceFound('no service found {}'.format(req.srv_name))
            #raise ConnectionError(
            #   'no available rpc server for {}'.format(req.srv_name))
        try:
            return await client.request_obj(
                req, timeout=timeout)
        except ConnectionError:
            assert not client.connected
            raise Retry()

pool = SimpleHttpPool()
