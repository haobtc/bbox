from typing import Dict, Any, List, Union, Iterable, Set, Optional, Awaitable, Callable, Tuple
import re
import weakref
import logging
import asyncio
import string
import ssl
import os
from decimal import Decimal
from json import (
    JSONEncoder,
    dumps as json_dumps,
    loads as json_loads
)
import netifaces
import random
from datetime import datetime, date
from .exceptions import ServiceError

def guess_json(p:str) -> Any:
    if p in ('null', 'true', 'false'):
        return json_loads(p)
    elif p.startswith('{') or p.startswith('['):
        return json_loads(p)
    elif p.startswith('"'):
        return json_loads(p)
    elif p.isdigit() or re.match(r'\-?\d+$', p):
        return int(p)
    elif re.match(r'\-?\d*(\.\d+)?$', p):
        return float(p)
    return p

def semanticbool(v:str) -> bool:
    if v.lower() in ('yes', 'true', 'ok', 'on', '1', 'y'):
        return True
    elif v.lower() in ('no', 'false', 'off', '0', 'n'):
        return False
    else:
        raise ValueError()

class BBoxJSONEncoder(JSONEncoder):
    def default(self, obj: Any) -> str:
        if isinstance(obj, datetime):
            return obj.replace(microsecond=0).isoformat()
        elif isinstance(obj, (Decimal, date)):
            return str(obj)
        return JSONEncoder.default(self, obj)

def json_pp(v: Any) -> str:
    return json_dumps(v, indent=2, sort_keys=True, cls=BBoxJSONEncoder)

def json_to_str(v: Any) -> str:
    return json_dumps(v, sort_keys=True, cls=BBoxJSONEncoder)

def map_bytes_to_str(alist: List[bytes], encoding:str='utf-8') -> List[str]:
    return [v.decode(encoding) for v in alist]

def import_module(spec: str) -> Any:
    mod = __import__(spec)
    for sec in spec.split('.')[1:]:
        mod = getattr(mod, sec)
    return mod

def assert_type(v:Any, t:Any) -> None:
    if not isinstance(v, t):
        raise TypeError()

def abs_path(path: str) -> str:
    return os.path.join(os.getcwd(), path)

def home_path(path: str) -> str:
    home:Optional[str] = os.getenv('HOME')
    assert home is not None
    return os.path.join(home, path)

def force_str(v: Any, encoding:str='utf-8') -> str:
    if type(v) == bytes:
        return v.decode(encoding)
    else:
        return str(v)

_localbox_ipset: Optional[Set[str]] = None

def get_localbox_ipset() -> Set[str]:
    global _localbox_ipset
    if _localbox_ipset is not None:
        return _localbox_ipset

    _localbox_ipset = set()
    for intf in netifaces.interfaces():
        for infos in netifaces.ifaddresses(intf).values():
            for info in infos:
                addr = info.get('addr')
                if addr and re.match(
                        r'\d+\.\d+\.\d+\.\d+', addr):
                    _localbox_ipset.add(addr)
    return _localbox_ipset

def localbox_ip(*iplist:str) -> Set[str]:
    return get_localbox_ipset().intersection(set(iplist))


def get_bbox_path(path:str) -> Optional[str]:
    rel_path = '.bbox/{}'.format(path)
    p:str
    for p in [
            abs_path(rel_path),
            home_path(rel_path),
            os.path.join('/etc/bbox', path)]:
        if os.path.exists(p):
            return p
    return None

def get_ssl_context(ssl_prefix:str) -> Optional[ssl.SSLContext]:
    if ssl_prefix:
        ssl_cert = get_bbox_path(
            'certs/{}/{}.crt'.format(ssl_prefix, ssl_prefix))
        assert ssl_cert

        ssl_key = get_bbox_path(
            'certs/{}/{}.key'.format(ssl_prefix, ssl_prefix))
        assert ssl_key
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH)
        #ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.load_cert_chain(
            ssl_cert, ssl_key)
        return ssl_context
    else:
        return None

def get_cert_ssl_context(ssl_prefix: str) -> Optional[ssl.SSLContext]:
    if ssl_prefix:
        ssl_cert = get_bbox_path(
            'certs/{}/{}.crt'.format(ssl_prefix, ssl_prefix))
        assert ssl_cert
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH,
            cafile=ssl_cert)
        return ssl_context
    else:
        return None

g_request_id: int = 0
def next_request_id() -> int:
    global g_request_id
    g_request_id += 1
    return g_request_id


# sleep tasks
g_sleep_tasks:weakref.WeakSet = weakref.WeakSet()
async def sleep(secs: float) -> Any:
    '''
    Interruptable sleep task
    '''
    loop = asyncio.get_event_loop()
    task:asyncio.Task = loop.create_task(asyncio.sleep(secs))
    g_sleep_tasks.add(task)
    try:
        return await task
    except asyncio.CancelledError:
        logging.debug('sleep task %s cancelled', task)
    finally:
        try:
            g_sleep_tasks.remove(task)
        except KeyError:
            # in case task is not in sleep_tasks
            logging.warn('sleep task %s is not in list', task)

def wakeup_sleep_tasks() -> None:
    for task in g_sleep_tasks:
        task.cancel()

def supervised_run(cor: Callable, args:Tuple=(), kwargs:Optional[Dict[str, Any]]=None, exc:Any=None, restart_sleep:float=0.01) -> None:
    from .cluster import get_cluster
    if kwargs is None:
        kwargs = {}
    async def __wrapped() -> None:
        while get_cluster().is_running():
            try:
                await cor(*args, **kwargs)
            except Exception as e:
                if exc and isinstance(e, exc):
                    logging.warn('except on supervised_run, will restart', exc_info=True)
                    await sleep(restart_sleep)
                else:
                    raise
    asyncio.ensure_future(__wrapped())
