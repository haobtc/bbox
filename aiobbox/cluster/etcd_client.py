from typing import Dict, Any, List, Tuple, Union, Iterable, Set, Optional, Callable
import logging
import uuid
import re
import random
import asyncio
import aio_etcd as etcd
#from aio_etcd.lock import Lock
import aiohttp
from collections import defaultdict
from aiobbox.exceptions import ETCDError
from .ticket import get_ticket

WrappedETCDFunc = Callable[..., Any]

logger = logging.getLogger('bbox')

class EtcdClient:
    etcdIndex = 0
    def path(self, p:str) -> str:
        ticket = get_ticket()
        if p.startswith('/'):
            return '/{}{}'.format(ticket.prefix, p)
        else:
            return '/{}/{}'.format(ticket.prefix, p)

    @property
    def prefix(self) -> str:
        return get_ticket().prefix

    def connect(self) -> None:
        self.client = None
        self.client_failed = False
        self.cont = True

        protocol = 'http'
        etcd_list = get_ticket().etcd
        if isinstance(etcd_list, dict):
            protocol = etcd_list['protocol']
            etcd_list = etcd_list['host']

        if len(etcd_list) == 1:
            host, port = etcd_list[0].split(':')
            self.client = etcd.Client(
                host=host,
                port=int(port),
                protocol=protocol,
                allow_reconnect=True,
                allow_redirect=True)
        else:
            def split_addr(e:str) -> Tuple[str, int]:
                host, port = e.split(':')
                return host, int(port)

            host_list = [split_addr(e)
                         for e in etcd_list]

            self.client = etcd.Client(
                host=tuple(host_list),
                protocol=protocol,
                allow_reconnect=True,
                allow_redirect=True)

    def close(self) -> None:
        if self.client:
            self.client.close()
        self.cont = False

    # etcd client wraps
    async def _wrap_etcd(self, fn:WrappedETCDFunc, *args, **kw) -> Any:
        try:
            r = await fn(*args, **kw)
            self.etcdIndex = max(r.etcd_index, self.etcdIndex)
            self.client_failed = False
            return r
        except aiohttp.ClientError as e:
            logger.warn('http client error', exc_info=True)
            self.client_failed = True
            raise ETCDError
        except etcd.EtcdConnectionFailed:
            #import traceback
            #traceback.print_exc()
            logger.warn('connection failed')
            self.client_failed = True
            raise ETCDError
        # except etcd.EtcdException:
        #     logger.warn('etcd exception', exc_info=True)
        #     self.client_failed = True
        #     raise ETCDError

    async def write(self, *args, **kw):
        return await self._wrap_etcd(self.client.write,
                                     *args, **kw)

    async def read(self, *args, **kw):
        return await self._wrap_etcd(self.client.read,
                                     *args, **kw)

    async def refresh(self, *args, **kw):
        return await self._wrap_etcd(self.client.refresh,
                                     *args, **kw)

    async def delete(self, *args, **kw):
        return await self._wrap_etcd(self.client.delete,
                                     *args, **kw)

    def walk(self, v):
        yield v
        for c in v.children:
            if c.key == v.key:
                continue
            for cc in self.walk(c):
                yield cc

    async def watch_changes(self, component, changed):
        await changed()
        last_index = self.etcdIndex + 1

        while self.cont:
            logger.debug('watching %s from index %s', component, last_index)
            #print('watch', component, last_index)
            try:
                # watch every 1 min to
                # avoid timeout exception
                chg = await asyncio.wait_for(
                    self.read(self.path(component),
                              recursive=True,
                              waitIndex=last_index,
                              wait=True),
                    timeout=10)
                logger.debug(
                    'watched change on %s, action %s, modified %s, etcd_index %s',
                    component, chg.action, chg.modifiedIndex,
                    chg.etcd_index)
                last_index = chg.modifiedIndex + 1
                await changed(chg)
            except asyncio.TimeoutError:
                logger.debug(
                    'timeout error during watching %s',
                    component)
            except ETCDError:
                logger.warn('etcd error, sleep for a while')
                await asyncio.sleep(1)
            await changed(None)


    def acquire_lock(self, name):
        return SimpleLock(self,
                          self.path('_lock/{}'.format(name)))

class SimpleLock:
    lock_keys: Dict[str, str] = {}

    @classmethod
    async def close_all_keys(cls, client):
        for key, u in cls.lock_keys.items():
            await client.delete(key)
        cls.lock_keys = {}

    async def __aenter__(self):
        return await self.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        return await self.release()

    def __init__(self, cc, path):
        self.client = cc
        self.path = path
        self.uuid = uuid.uuid4().hex
        self.key = None
        self.cont = True
        self._acquired = False

    @property
    def is_acquired(self):
        return self._acquired

    async def acquire(self):
        if self.client.client_failed:
            raise ETCDError
        r = await self.client.write(self.path, self.uuid, ttl=5, append=True)
        self.key = r.key
        self.lock_keys[r.key] = self.uuid
        asyncio.ensure_future(self.keep_key())
        await self.wait_key()
        return self

    async def release(self):
        if not self.cont and self.client.client_failed:
            return
        if self.key:
            await self.client.delete(self.key)
            self.lock_keys.pop(self.key, None)
            self.key = None
        else:
            r = await self.client.read(self.path,
                                       recursive=True)
            for n in self.walk(r):
                if n.value == self.uuid:
                    await self.client.delete(n.key)

        self._acquired = False
        self.cont = False

    async def check_acquired(self):
        if self.client.client_failed:
            self.cont = False
            return False
        try:
            r = await self.client.read(self.path,
                                       sorted=True,
                                       recursive=True)
        except ETCDError:
            self.cont = False
            return False
        waiters = []
        for n in self.client.walk(r):
            if self.path == n.key:
                continue
            rest_key = n.key[len(self.path):]
            if re.match(r'/?(?P<name>[^/]+)$', rest_key):
                waiters.append(n.key)
        if waiters:
            # if self.key is the first element
            # then the lock is acquired
            if waiters[0] == self.key:
                self._acquired = True
                return True
        return False

    async def wait_key(self) -> None:
        while self.cont and not (await self.check_acquired()):
            try:
                chg = await asyncio.wait_for(
                    self.client.read(self.path,
                                     wait=True,
                                     recursive=True),
                    timeout=20)
            except ETCDError:
                self.cont = False
                continue
            except asyncio.TimeoutError:
                continue
            if (chg.action not in ('delete', 'expire')
                or chg.key > self.key):
                # not interest
                continue

            #await asyncio.sleep(0.1)

    async def keep_key(self) -> None:
        while self.cont and self.key:
            try:
                await self.client.refresh(self.key, ttl=5)
            except etcd.EtcdKeyNotFound:
                pass
            except ETCDError:
                await self.release()
                #loop = asyncio.get_event_loop()
                #loop.stop()
                break
            await asyncio.sleep(1)
