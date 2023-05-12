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

BOX_TTL = 6

class BoxAgent:
    srv_names: List[str]
    bind: str = ''
    extbind: str = ''
    etcd_client: EtcdClient

    def __init__(self) -> None:
        super(BoxAgent, self).__init__()
        self.ssl_prefix: Optional[str] = None
        self.started: bool = False
        self.etcd_client = EtcdClient()
        self.override_ticket: Dict[str, Any] = {}

    def set_cont(self, cont: bool) -> None:
        self.etcd_client.cont = cont
    def get_cont(self) -> bool:
        return self.etcd_client.cont
    cont = property(get_cont, set_cont)

    async def start(self, boxid: str, srv_names: List[str], **ticket) -> None:
        assert not self.started
        assert boxid

        self.boxid = boxid
        self.srv_names = srv_names

        self.bind = ''
        self.extbind = ''

        str_port = ticket.get('port')
        if str_port:
            if ':' in str_port:
                port_start, port_end = [int(v) for v in str_port.split(':')]
            else:
                port_start = int(str_port)
                port_end = port_start + 1
            ticket['port_range'] = [port_start, port_end]

        self.override_ticket = ticket

        self.etcd_client.connect()
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
        port_range = None
        if self.override_ticket.get('port_range'):
            port_range = self.override_ticket['port_range']

        if self.override_ticket.get('bind_ip'):
            ticket.bind_ip = self.override_ticket['bind_ip']

        if self.override_ticket.get('extbind'):
            ticket.extbind = self.override_ticket['extbind']

        for retry_t in range(retry + 1):
            if self.bind:
                return

            if port_range is None:
                port_range = self.get_box_config(
                    'port_range',
                    default=ticket.port_range)

            assert len(port_range) == 2, f'port_range is {port_range}'
            assert port_range[0] < port_range[1], 'invalid port range {}'.format(port_range)

            port_choices = range(*port_range)

            # choose a relatively fixed port to keep serve
            digest = int(md5('{}.{}'.format(self.boxid, retry_t).encode()).hexdigest(), 16)
            port_index = digest % len(port_choices)
            port = port_choices[port_index]
            assert port >= port_choices[0], 'port {} is too small'.format(port)
            assert port <= port_choices[-1], 'port {} is too big'.format(port)

            extbind = ticket.extbind
            if not extbind:
                # combine external bind info
                extbind = '{}:{}'.format(ticket.bind_ip, port)
            elif ':' not in extbind:
                # use random selected port if not specified
                extbind = '{}:{}'.format(extbind, port)

            key = f'boxes/{extbind}'
            value = self.box_info(extbind=extbind)
            try:
                await self.etcd_client.write_n_keep(key, value, BOX_TTL)
                self.extbind = extbind
                self.bind = '{}:{}'.format(ticket.bind_ip, port)
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
        if not self.bind or not self.etcd_client:
            return
        key = f'boxes/{self.bind}'
        try:
            await self.etcd_client.delete(key)
        except ETCDError:
            pass
        logging.info('box %s deregistered from cluster', self.boxid)

    # async def update(self, key: str) -> None:
    #     #key = f'boxes/{self.bind}'
    #     await self.etcd_client.keep_key(key, BOX_TTL)

_agent = BoxAgent()
def get_box() -> BoxAgent:
    return _agent
