import logging
import re
import random
import json
import time
import asyncio
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
    def __init__(self):
        super(BoxAgent, self).__init__()
        self.ssl_prefix = None
        self.started = False

    async def start(self, boxid, srv_names):
        assert not self.started
        assert boxid

        self.boxid = boxid
        self.srv_names = srv_names
        self.bind = None
        self.extbind = None
        self.connect()
        await self.register()
        self.started = True

    def box_info(self, extbind=None):
        extbind = extbind or self.extbind
        return json_to_str({
            'bind': extbind,
            'start_time': datetime.now(tzlocal()),
            'ssl': self.ssl_prefix,
            'boxid': self.boxid,
            'services': self.srv_names})

    def get_box_config(self, key, default=None):
        config = get_sharedconfig()
        return config.get_chain(
            ['box.{}'.format(self.boxid),
             'box.default'],
            key,
            default=default)

    async def register(self, retry=100):
        cfg = get_ticket()
        for _ in range(retry + 1):
            if self.bind:
                return

            port_range = self.get_box_config(
                'port_range',
                default=cfg.port_range)

            assert port_range[0] < port_range[1]
            port = random.randrange(*port_range)

            extbind = cfg.extbind
            if not extbind:
                extbind = '{}:{}'.format(cfg.bind_ip, port)

            key = self.path('boxes/{}'.format(extbind))
            value = self.box_info(extbind=extbind)
            try:
                await self.write(key, value,
                                 ttl=BOX_TTL,
                                 prevExist=False)
                self.extbind = extbind
                self.bind = '{}:{}'.format(cfg.bind_ip, port)
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

    async def deregister(self):
        self.cont = False
        if not self.bind or not self.client:
            return
        key = self.path('boxes/{}'.format(self.bind))
        try:
            await self.delete(key)
        except ETCDError:
            pass

    async def update(self):
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
def get_box():
    return _agent
