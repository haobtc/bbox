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

def guess_json(p):
    if p in ('null', 'true', 'false'):
        p = json_loads(p)
    elif p.startswith('{') or p.startswith('['):
        p = json_loads(p)
    elif p.startswith('"'):
        p = json_loads(p)
    elif p.isdigit() or re.match(r'\-?\d+$', p):
        p = int(p)
    elif re.match(r'\-?\d*(\.\d+)?$', p):
        p = float(p)
    return p

def semanticbool(v):
    if v.lower() in ('yes', 'true', 'ok', 'on', '1', 'y'):
        return True
    elif v.lower() in ('no', 'false', 'off', '0', 'n'):
        return False
    else:
        raise ValueError()

class BBoxJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.replace(microsecond=0).isoformat()
        elif isinstance(obj, (Decimal, date)):
            return str(obj)
        return JSONEncoder.default(self, obj)

def json_pp(v):
    return json_dumps(v, indent=2, sort_keys=True, cls=BBoxJSONEncoder)

def json_to_str(v):
    return json_dumps(v, sort_keys=True, cls=BBoxJSONEncoder)

def map_bytes_to_str(alist, encoding='utf-8'):
    return [v.decode(encoding) for v in alist]

def import_module(spec):
    mod = __import__(spec)
    for sec in spec.split('.')[1:]:
        mod = getattr(mod, sec)
    return mod

def parse_int(v):
    assert isinstance(v, int)
    return v

def parse_float(v):
    assert isinstance(v, (int, float, long))
    return v

def parse_str(v):
    assert isinstance(v, str)

def assert_type(v, t):
    assert isinstance(v, t)

def abs_path(path):
    return os.path.join(os.getcwd(), path)

def home_path(path):
    return os.path.join(os.getenv('HOME'), path)

def force_str(v, encoding='utf-8'):
    if type(v) == bytes:
        return v.decode(encoding)
    else:
        return str(v)

_localbox_ipset = None
def get_localbox_ipset():
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

def localbox_ip(*iplist):
    return get_localbox_ipset().intersection(set(iplist))


def get_bbox_path(path):
    rel_path = '.bbox/{}'.format(path)
    for path in [
            abs_path(rel_path),
            home_path(rel_path),
            os.path.join('/etc/bbox', path)]:
        if os.path.exists(path):
            return path

def get_ssl_context(ssl_prefix):
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

def get_cert_ssl_context(ssl_prefix):
    if ssl_prefix:
        ssl_cert = get_bbox_path(
            'certs/{}/{}.crt'.format(ssl_prefix, ssl_prefix))
        assert ssl_cert
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH,
            cafile=ssl_cert)
        return ssl_context

g_request_id = 0
def next_request_id():
    global g_request_id
    g_request_id += 1
    return g_request_id


# sleep tasks
g_sleep_tasks = weakref.WeakSet()
async def sleep(secs):
    '''
    Interruptable sleep task
    '''
    loop = asyncio.get_event_loop()
    task = loop.create_task(asyncio.sleep(secs))
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

def wakeup_sleep_tasks():
    for task in g_sleep_tasks:
        task.cancel()
