import logging
import re
import random
import asyncio
import aio_etcd as etcd
import aiohttp
from collections import defaultdict
from aiobbox.exceptions import ETCDError
from .cfg import get_localconfig

class EtcdClient:
    def path(self, p):
        cfg = get_localconfig()
        if p.startswith('/'):
            return '/{}{}'.format(cfg.prefix, p)
        else:
            return '/{}/{}'.format(cfg.prefix, p)
        
    @property
    def prefix(self):
        return get_localconfig().prefix

    def connect(self):
        self.client = None
        self.client_failed = False
        self.cont = True
        
        etcd_list = get_localconfig().etcd
        if len(etcd_list) == 1:
            host, port = etcd_list[0].split(':')
            self.client = etcd.Client(
                host=host,
                port=int(port),
                allow_reconnect=True,
                allow_redirect=True)
        else:
            host = tuple(tuple(e.split(':'))
                         for e in etcd_list)
            self.client = etcd.Client(
                host=host,
                allow_reconnect=True,
                allow_redirect=True)

    def close(self):
        if self.client:
            self.client.close()
        self.cont = False

    # etcd client wraps
    async def _wrap_etcd(self, fn, *args, **kw):
        try:
            r = await fn(*args, **kw)
            self.client_failed = False
            return r
        except aiohttp.ClientError as e:
            logging.warn('http client error', exc_info=True)
            self.client_failed = True
            raise ETCDError
        except etcd.EtcdKeyNotFound:
            raise
        except (etcd.EtcdException, etcd.EtcdConnectionFailed):
            import traceback
            traceback.print_exc()
            logging.warn('connection failed')
            self.client_failed = True
            raise ETCDError

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
        while self.cont:
            logging.debug('watching %s', component)
            try:
                chg = await asyncio.wait_for(
                    self.read(self.path(component),
                              recursive=True,
                              wait=True),
                    timeout=60)
                await changed(chg)
            except asyncio.TimeoutError:
                logging.warn(
                    'timeout error during watching %s',
                    component)
            except ETCDError:
                logging.warn('etcd error, sleep for a while')
                await asyncio.sleep(1)
            await changed(None)

            
            
