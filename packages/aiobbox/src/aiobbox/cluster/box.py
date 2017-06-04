import logging
import re
import random
import json
import time
import asyncio
import aio_etcd as etcd
from aiobbox.utils import json_to_str
from aiobbox.exceptions import RegisterFailed, ETCDError
import aiobbox.config as bbox_config
from .etcd_client import EtcdClient

BOX_TTL = 10

class BoxAgent(EtcdClient):
    agent = None

    @classmethod
    async def start_box(cls, boxid, srv_names, **local_config):
        if cls.agent:
            return cls.agent

        cls.agent = cls(boxid=boxid, **local_config)
        cls.agent.connect()
        await cls.agent.register(srv_names)
        return cls.agent
    
    def __init__(self, boxid='', prefix='', etcd=None, port_range=None, bind_ip='127.0.0.1', **kw):
        super(BoxAgent, self).__init__(etcd, prefix)
        self.boxid = boxid
        self.port_range = port_range if port_range else (30000, 40000)
        self.bind_ip = bind_ip
        self.bind = None
        self.srv_names = []

    def box_info(self, bind=None):
        bind = bind or self.bind
        return json_to_str({
            'bind': bind,
            'boxid': self.boxid,
            'services': self.srv_names})

    async def register(self, srv_names, retry=100):
        self.srv_names = srv_names
        for _ in range(retry + 1):
            if self.bind:
                return
            port = random.randrange(*self.port_range)
            bind = '{}:{}'.format(self.bind_ip,
                                  port)

            key = self.path('boxes/{}'.format(bind))
            value = self.box_info(bind)
            try:
                await self.write(key, value,
                                 ttl=BOX_TTL,
                                 prevExist=False)
                self.bind = bind
                asyncio.ensure_future(self.update())
                return
            except ETCDError:
                await asyncio.sleep(0.1)
            except etcd.EtcdAlreadyExist:
                logging.warn(
                    'register key conflict {}'.format(key))
                await asyncio.sleep(0.1)

        raise RegisterFailed(
            'no port alloced after retry {} times'.format(retry))

    async def deregister(self):
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
            if not self.client or not self.bind:
                logging.debug('etcd client or bind are empty')
            else:
                key = self.path('boxes/{}'.format(self.bind))
                value = self.box_info()
                try:
                    await self.write(key, value, ttl=BOX_TTL)
                except etcd.EtcdKeyNotFound:
                    logging.warn('etcd key not found %s', key)
                except ETCDError:
                    logging.debug('etcd error on refresh')

