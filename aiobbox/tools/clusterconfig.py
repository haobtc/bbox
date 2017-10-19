import os, sys
import re
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.cluster import get_cluster, get_sharedconfig
from aiobbox.utils import guess_json, json_pp
from aiobbox.handler import BaseHandler

async def get_config(args):
    sec_key = args.sec_key
    if '/' in sec_key:
        sec, key = sec_key.split('/')
        r = get_sharedconfig().get_strict(sec, key)
    else:
        r = get_sharedconfig().get_section_strict(sec_key)
    print(json_pp(r))

async def set_config(args):
    sec, key = args.sec_key.split('/')
    value = guess_json(args.value)
    return await get_cluster().set_config(sec, key, value)

async def del_config(args):
    sec_key = args.sec_key
    if '/' in sec_key:
        sec, key = sec_key.split('/')
        return await get_cluster().del_config(sec, key)
    else:
        return await get_cluster().del_section(sec_key)

async def clear_config(args):
    return await get_cluster().clear_config()

async def dump_config(args):
    data = get_sharedconfig().dump_json()
    print(data)

async def load_config(args):
    jsonfile = args.jsonfile
    with open(jsonfile, 'r', encoding='utf-8') as f:
        new_sections = json.load(f)
    rem_set, add_set = get_sharedconfig().compare_sections(
        new_sections)
    if args.purge:
        for sec, key, value in rem_set:
            print("delete", sec, key)
            await get_cluster().del_config(sec, key)

    for sec, key, value in add_set:
        value = json.loads(value)
        print("set", sec, key)
        await get_cluster().set_config(sec, key, value)

class Handler(BaseHandler):
    help = 'bbox config'
    def add_arguments(self, parser):
        subp = parser.add_subparsers()
        p = subp.add_parser('get', help='get config')
        p.add_argument(
            'sec_key',
            type=str,
            help='sec/key or sec')
        p.set_defaults(func=get_config)

        p = subp.add_parser('set', help='set config')
        p.add_argument(
            'sec_key',
            type=str,
            help='sec/key or sec')

        p.add_argument(
            'value',
            type=str,
            help='value')
        p.set_defaults(func=set_config)

        p = subp.add_parser('clear', help='clear config')
        p.set_defaults(func=clear_config)

        p = subp.add_parser('dump', help='dump config')
        p.set_defaults(func=dump_config)

        p = subp.add_parser('list', help='list config')
        p.set_defaults(func=dump_config)

        p = subp.add_parser('load', help='load config from file')
        p.add_argument(
            'jsonfile',
            type=str,
            help='config file in json format')
        p.add_argument(
            '--purge',
            type=bool,
            default=False,
            help='delete old config items different from the local file')
        p.set_defaults(func=load_config)

        p = subp.add_parser('del', help='delete config')
        p.add_argument(
            'sec_key',
            type=str,
            help='sec/key or sec')
        p.set_defaults(func=del_config)

    async def run(self, args):
        await get_cluster().start()
        func = getattr(args, 'func', None)
        if func:
            try:
                await args.func(args)
            finally:
                c = get_cluster()
                c.cont = False
                await asyncio.sleep(0.1)
                c.close()
        else:
            print('type bbox.py config -h')
