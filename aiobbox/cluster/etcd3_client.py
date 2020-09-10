from typing import Optional, Union, Callable
import logging
import asyncio
from aioetcdm3.client import Client, prefix_range_end

from .ticket import get_ticket

logger = logging.getLogger(__name__)

class EtcdClient:
    cont: bool = False
    _client: Client

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
        #self._client = None
        self.cont = True

        protocol = 'http'
        etcd_list = get_ticket().etcd
        if isinstance(etcd_list, dict):
            protocol = etcd_list['protocol']
            etcd_list = etcd_list['host']

        etcd_addr = '{}://{}'.format(protocol, etcd_list[0])
        self._client = Client(etcd_addr)
        asyncio.ensure_future(self._client.collect_members())

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
        self.cont = False

    async def read_components(self, component: str):
        start = self._path(component)
        end = prefix_range_end(start)
        r = await self._client.kv.get_range(start, end)
        for kv in r.kvs:
            yield kv

    async def read(self, key: str, **kw):
        key = self._path(key)
        return await self._client.kv.get(key)

    async def write(self, key: str, value: str, prevValue: Union[str, None]=None, **kw):
        key = self._path(key)
        resp = await self._client.kv.put(key, value, expect_prev_value=prevValue)

    async def delete(self, key: str, **kw) -> None:
        key = self._path(key)
        await self._client.kv.delete(key)

    async def watch_changes(self, component: str, changed: Callable) -> None:
        start = self._path(component)
        end = prefix_range_end(start)
        async for chg in self._client.watch.open_stream((start, end)):
            await changed(chg)

    async def write_n_keep(self, key: str, value: str, ttl: int) -> None:
        key = self._path(key)
        lease = await self._client.lease.grant(ttl)
        await self._client.kv.put(key, value, lease_id=lease.ID)
        asyncio.ensure_future(self._client.lease.keep_alive(lease.ID))




