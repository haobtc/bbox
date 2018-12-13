from typing import Dict, Any, List, Union, Iterable, Set, Optional
import logging
import re
import json
import time
import asyncio
from hashlib import md5
from datetime import datetime
from dateutil.tz import tzlocal
import aio_etcd as etcd
from aiobbox.utils import json_to_str
from aiobbox.exceptions import RegisterFailed, ETCDError
from .etcd_client import EtcdClient
from .ticket import get_ticket
from .cfg import get_sharedconfig

logger = logging.getLogger('bbox')

BOX_TTL = 10

class BoxAgent(EtcdClient):
    srv_names: List[str]
    bind: str = ''
    extbind: str = ''

    def __init__(self) -> None:
        super(BoxAgent, self).__init__()
        self.ssl_prefix: Optional[str] = None
        self.started: bool = False

    async def start(self, boxid: str, srv_names: List[str]) -> None:
        assert not self.started
        assert boxid

        self.boxid = boxid
        self.srv_names = srv_names
        self.bind = ''
        self.extbind = ''
        self.connect()
        await self.register()
        self.started = True

    def box_info(self, extbind: str=None) -> str:
        extbind = extbind or self.extbind
        return json_to_str({
            'bind': extbind,
            'start_time': datetime.now(tzlocal()),
            'ssl': self.ssl_prefix,
            'boxid': self.boxid,
            'services': self.srv_names})

    def get_box_config(self, key: str, default:Any=None) -> Any:
        config = get_sharedconfig()
        return config.get_chain(
            ['box.{}'.format(self.boxid),
             'box.default'],
            key,
            default=default)

    async def register(self, retry:int=100) -> None:
        ticket = get_ticket()
        for retry_t in range(retry + 1):
            if self.bind:
                return

            port_range = self.get_box_config(
                'port_range',
                default=ticket.port_range)

            assert len(port_range) == 2
            assert port_range[0] < port_range[1], 'invalid port range {}'.format(port_range)

            port_range = range(*port_range)

            # choose a relatively fixed port to keep serve
            digest = int(md5('{}.{}'.format(self.boxid, retry_t).encode()).hexdigest(), 16)
            port_index = digest % len(port_range)
            port = port_range[port_index]
            assert port >= port_range[0], 'port {} is too small'.format(port)
            assert port <= port_range[-1], 'port {} is too big'.format(port)

            extbind = ticket.extbind
            if not extbind:
                # combine external bind info
                extbind = '{}:{}'.format(ticket.bind_ip, port)
            elif ':' not in extbind:
                # use random selected port if not specified
                extbind = '{}:{}'.format(extbind, port)

            key = self.path('boxes/{}'.format(extbind))
            value = self.box_info(extbind=extbind)
            try:
                await self.write(key, value,
                                 ttl=BOX_TTL,
                                 prevExist=False)
                self.extbind = extbind
                self.bind = '{}:{}'.format(ticket.bind_ip, port)
                asyncio.ensure_future(self.update())
                return
            except ETCDError:
                await asyncio.sleep(0.1)
            except etcd.EtcdAlreadyExist:
                logger.warn(
                    'register key conflict {}'.format(key))
                await asyncio.sleep(0.1)

        raise RegisterFailed(
            'no port alloced after retry {} times'.format(retry))

    async def deregister(self) -> None:
        self.cont = False
        if not self.bind or not self.client:
            return
        key = self.path('boxes/{}'.format(self.bind))
        try:
            await self.delete(key)
        except ETCDError:
            pass
        logging.debug('box %s deregistered from cluster', self.boxid)

    async def update(self) -> None:
        while self.cont:
            await asyncio.sleep(3)
            if not self.cont:
                break
            if not self.client or not self.bind:
                logger.debug('etcd client or bind are empty')
            else:
                key = self.path('boxes/{}'.format(self.bind))
                try:
                    await self.refresh(key, ttl=BOX_TTL)
                except etcd.EtcdKeyNotFound:
                    logger.warn('etcd key not found %s', key)
                    value = self.box_info()
                    try:
                        await self.write(key, value, ttl=BOX_TTL)
                    except ETCDError:
                        logger.warn('etc error on write')
                except ETCDError:
                    logger.warn('etcd error on refresh')

_agent = BoxAgent()
def get_box() -> BoxAgent:
    return _agent
