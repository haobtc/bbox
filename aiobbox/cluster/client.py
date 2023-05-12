from typing import Dict, Any, List, Union, Iterable, Set
import logging
import re
import os
import random
import json
import time
import asyncio
import aio_etcd as etcd
import aiohttp
from collections import defaultdict
from aiobbox.utils import json_to_str, localbox_ip, force_str, get_bbox_path
from aiobbox.exceptions import RegisterFailed, ETCDError
from .etcd_client import EtcdClient

from .cfg import SharedConfig, get_sharedconfig

logger = logging.getLogger('bbox')

class ClientAgent:
    state: str = 'INIT'
    etcd_client: EtcdClient

    def __init__(self) -> None:
        super(ClientAgent, self).__init__()
        self.state = 'INIT'
        self.etcd_client = EtcdClient()

    async def start(self) -> None:
        self.route: Dict[str, List[str]] = defaultdict(list)
        self.boxes: Dict[str, Any] = {}

        self.etcd_client.connect()

        await self.get_boxes()
        await self.get_configs()

        asyncio.ensure_future(self._watch_boxes())
        asyncio.ensure_future(self._watch_configs())
        self.state = 'STARTED'

    def stop(self) -> None:
        self.state = 'STOPPING'

    def is_started(self) -> bool:
        return self.state == 'STARTED'
    is_running = is_started

    def is_stopping(self) -> bool:
        return self.state == 'STOPPING'

    def get_local_boxes(self) -> Iterable[str]:
        for bind in self.boxes.keys():
            if localbox_ip(bind.split(':')[0]):
                yield bind

    async def get_boxes(self, _chg:Any=None):
        new_route: Dict[str, List[str]] = defaultdict(list)
        boxes = {}
        async for v in self.etcd_client.read_components('boxes'):
            m = re.match(r'/[^/]+/boxes/(?P<box>[^/]+)$', force_str(v.key))
            if not m:
                continue
            if not v.value:
                #logger.warn('v has no value %s', v)
                continue
            box_info = json.loads(v.value)
            bind = box_info['bind']
            boxes[bind] = box_info
            for srv in box_info['services']:
                new_route[srv].append(bind)

        self.route = new_route
        self.boxes = boxes

    def get_box(self, srv):
        boxes = self.route[srv]
        return random.choice(boxes)

    async def _watch_boxes(self):
        return await self.etcd_client.watch_changes(
            'boxes',
            self.get_boxes)

    # config related
    async def set_config(self, sec: str, key: str, value: Any, save: bool=True) -> None:
        assert sec and key
        assert '/' not in sec
        assert '/' not in key

        shared_cfg = get_sharedconfig()
        if save:
            etcd_key = f'configs/{sec}/{key}'
            old_value = shared_cfg.get(sec, key)
            value_json = json_to_str(value)
            if old_value:
                old_value_json = json_to_str(old_value)
                await self.etcd_client.write(
                    etcd_key, value_json,
                    prevValue=old_value_json)
            else:
                await self.etcd_client.write(
                    etcd_key, value_json,
                    prevExist=False)
        shared_cfg.set(sec, key, value)

    async def del_config(self, sec:str, key:str) -> None:
        assert sec and key
        assert '/' not in sec
        assert '/' not in key

        get_sharedconfig().delete(sec, key)
        etcd_key = f'configs/{sec}/{key}'
        await self.etcd_client.delete(etcd_key)

    async def del_section(self, sec: str) -> None:
        assert sec
        assert '/' not in sec

        get_sharedconfig().delete_section(sec)
        etcd_key = f'configs/{sec}'
        await self.etcd_client.delete(etcd_key, recursive=True)

    async def clear_config(self) -> None:
        get_sharedconfig().clear()
        try:
            await self.etcd_client.delete('configs', recursive=True)
        except etcd.EtcdKeyNotFound:
            logger.debug(
                'key %s not found on delete', 'configs')

    async def local_get_configs(self, cfg_path: str) -> None:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            new_sections = json.load(f)
        rem_set, add_set = get_sharedconfig().compare_sections(
            new_sections)
        if True:
            for sec, key, value in rem_set:
                await self.del_config(sec, key)

        for sec, key, value in add_set:
            value = json.loads(value)
            await self.set_config(sec, key, value, save=False)

    def use_local_configs(self) -> bool:
        shared_cfg_path = get_bbox_path('sharedconfig.json')
        return not not (shared_cfg_path and os.path.exists(shared_cfg_path))

    async def get_configs(self, _chg:Any=None) -> None:
        shared_cfg_path = get_bbox_path('sharedconfig.json')
        if shared_cfg_path and os.path.exists(shared_cfg_path):
            return await self.local_get_configs(shared_cfg_path)

        reg = r'/(?P<prefix>[^/]+)/configs/(?P<sec>[^/]+)/(?P<key>[^/]+)'

        new_conf = SharedConfig()
        async for v in self.etcd_client.read_components('configs'):
            m = re.match(reg, force_str(v.key))
            if m:
                assert m.group('prefix') == self.etcd_client.prefix
                sec = m.group('sec')
                key = m.group('key')
                new_conf.set(sec, key, json.loads(v.value))

        curr_conf = get_sharedconfig()
        delete_set, add_set = curr_conf.compare_sections(
            new_conf.sections)
        if delete_set or add_set:
            curr_conf.replace_with(new_conf)

    async def _watch_configs(self):
        if self.use_local_configs():
            logger.debug('use local configs')
            return

        return await self.etcd_client.watch_changes(
            'configs', self.get_configs)

    def close(self):
        return self.etcd_client.close()

_agent = ClientAgent()
def get_cluster():
    return _agent
