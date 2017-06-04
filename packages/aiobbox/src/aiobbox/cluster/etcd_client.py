import logging
import re
import random
import asyncio
import aio_etcd as etcd
import aiohttp
from collections import defaultdict
from aiobbox.exceptions import ETCDError
import aiobbox.config as bbox_config

class EtcdClient:
    def __init__(self, etcd_list, prefix):
        assert etcd_list
        assert prefix
        self.etcd_list = etcd_list
        self.prefix = prefix
        self.client = None
        self.client_failed = False
        self.cont = True

    def path(self, p):
        if p.startswith('/'):
            return '/{}{}'.format(self.prefix, p)
        else:
            return '/{}/{}'.format(self.prefix, p)

    def connect(self):
        if len(self.etcd_list) == 1:
            host, port = self.etcd_list[0].split(':')
            self.client = etcd.Client(
                host=host,
                port=int(port),
                allow_reconnect=True,
                allow_redirect=True)
        else:
            host = tuple(tuple(e.split(':')) for e in self.etcd_list)
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
                chg = await self.read(self.path(component),
                                      recursive=True,
                                      wait=True)
                await changed(chg)
            except asyncio.TimeoutError:
                logging.debug(
                    'timeout error during watching %s',
                    component)
            except ETCDError:
                logging.debug('etcd error, sleep for a while')
                await asyncio.sleep(1)
            except Exception as e:
                print('xxxx', e)
                raise
