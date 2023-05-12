from typing import Dict, Any, List, Tuple, Union, Iterable, Set, Optional, Callable
import logging
import uuid
import re
import random
import asyncio
import aio_etcd as etcd
import aiohttp
from aiobbox.exceptions import ETCDError
from .ticket import get_ticket

WrappedETCDFunc = Callable[..., Any]

logger = logging.getLogger(__name__)

class EtcdClient:
    etcdIndex: int = 0
    cont: bool = False
    _client: Optional[etcd.Client]

    def _path(self, p:str) -> str:
        ticket = get_ticket()
        if p.startswith('/'):
            return '/{}{}'.format(ticket.prefix, p)
        else:
            return '/{}/{}'.format(ticket.prefix, p)

    @property
    def prefix(self) -> str:
        return get_ticket().prefix

    @property
    def ready(self) -> bool:
        return not not self._client

    def connect(self) -> None:
        self._client = None
        self._client_failed = False
        self.cont = True

        protocol = 'http'
        etcd_list = get_ticket().etcd
        if isinstance(etcd_list, dict):
            protocol = etcd_list['protocol']
            etcd_list = etcd_list['host']

        if len(etcd_list) == 1:
            host, port = etcd_list[0].split(':')
            self._client = etcd.Client(
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

            self._client = etcd.Client(
                host=tuple(host_list),
                protocol=protocol,
                allow_reconnect=True,
                allow_redirect=True)

    def close(self) -> None:
        if self._client:
            self._client.close()
        self.cont = False

    # etcd client wraps
    async def _wrap_etcd(self, fn: WrappedETCDFunc, *args, **kw) -> Any:
        try:
            r = await fn(*args, **kw)
            self.etcdIndex = max(r.etcd_index, self.etcdIndex)
            self._client_failed = False
            return r
        except aiohttp.ClientError as e:
            logger.warning('http client error', exc_info=True)
            self._client_failed = True
            raise ETCDError
        except etcd.EtcdConnectionFailed:
            #import traceback
            #traceback.print_exc()
            logger.warning('connection failed')
            self._client_failed = True
            raise ETCDError
        except etcd.EtcdEventIndexCleared:
            logger.debug('etcd event index cleared')
            self._client_failed = True
            raise
        except etcd.EtcdKeyNotFound as e:
            logger.debug('etcd not found, %s', e)
            self._client_failed = True
            raise
        except etcd.EtcdException: # type: ignore
            logger.warning('etcd exception %s', fn, exc_info=True)
            self._client_failed = True
            raise

    async def write(self, key, value, **kw):
        key = self._path(key)
        return await self._wrap_etcd(
            self._client.write,
            key, value, **kw)

    async def read(self, key, **kw):
        key = self._path(key)
        return await self._wrap_etcd(
            self._client.read,
            key, **kw)

    async def refresh(self, key, **kw):
        key = self._path(key)
        return await self._wrap_etcd(
            self._client.refresh, key, **kw)

    async def delete(self, key, **kw):
        key = self._path(key)
        try:
            return await self._wrap_etcd(
                self._client.delete,
                key, **kw)
        except etcd.EtcdKeyNotFound:
            logger.warning('on delete, ectd key not found %s', key)

    def _walk(self, v):
        yield v
        for c in v.children:
            if c.key == v.key:
                continue
            for cc in self._walk(c):
                yield cc

    async def read_components(self, component: str):
        try:
            r = await self.read(component, recursive=True)
            for v in self._walk(r):
                yield v
        except etcd.EtcdKeyNotFound:
            pass

    async def watch_changes(self, component:str, changed:Callable) -> None:
        #last_index = self.etcdIndex + 1
        last_index = None

        while self.cont:
            if last_index is None:
                await changed()
            logger.debug('watching %s from index %s', component, last_index)
            #print('watch', component, last_index)
            try:
                # watch every 1 min to
                # avoid timeout exception
                chg = await asyncio.wait_for(
                    self.read(self._path(component),
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
            except etcd.EtcdEventIndexCleared:
                logger.debug('etcd event index cleared')
                last_index = None
            except ETCDError:
                logger.warning('etcd error, sleep for a while')
                await asyncio.sleep(1)
            #await changed(None)

    async def write_n_keep(self, key: str, value: str, ttl: int) -> None:
        await self.write(key, value, ttl=ttl, prevExist=False)
        asyncio.ensure_future(self.keep_key(key, value, ttl))


    async def keep_key(self, key: str, value: str, ttl: int) -> None:
        while self.cont:
            await asyncio.sleep(3)
            if not self.cont:
                break
            if not self.ready:
                logger.debug('etcd client not ready')
            else:
                try:
                    await self.refresh(key, ttl=ttl)
                except etcd.EtcdKeyNotFound:
                    logger.warning('etcd key not found %s', key)
                    #value = self.box_info()
                    try:
                        await self.write(key, value, ttl=ttl)
                    except ETCDError:
                        logger.warning('etc error on write')
                except ETCDError:
                    logger.warning('etcd error on refresh')

