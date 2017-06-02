import os, sys
import re
import json
import asyncio
import argparse
import aiotup.client as tup_client
import aiotup.config as tup_config
import aiotup.discovery as tup_dsc
from aiotup.utils import guess_json, json_dumps

parser = argparse.ArgumentParser(
    description='test an rpc interface')

parser.add_argument(
    'op',
    type=str,
    help='config operations')

parser.add_argument(
    'param',
    type=str,
    nargs='*',
    help='params')

async def get_config(sec_key):
    if '/' in sec_key:
        sec, key = sec_key.split('/')
        r = tup_config.grand.get_strict(sec, key)
    else:
        r = tup_config.grand.get_section_strict(sec_key)
    print(json_dumps(r))

async def set_config(sec_key, value):
    sec, key = sec_key.split('/')
    value = guess_json(value)
    return await tup_dsc.client_agent.set_config(sec, key, value)

async def del_config(sec_key):
    if '/' in sec_key:
        sec, key = sec_key.split('/')
        return await tup_dsc.client_agent.del_config(sec, key)
    else:
        return await tup_dsc.client_agent.del_section(sec_key)

async def clear_config():
    return await tup_dsc.client_agent.clear_config()

async def list_config():
    data = tup_config.grand.dump_json()
    print(data)

def help(f=sys.stdout):
    print('Commands', file=f)
    print(' get sec.key|sec  - get config or section', file=f)
    print(' set sec.key value  - set config', file=f)
    print(' list  - list configs', file=f)
    print(' del sec.key|sec  - delete config or section', file=f)
    print(' clear  - clear configs', file=f)

async def main():
    tup_config.parse_local()
    args = parser.parse_args()
    try:
        await tup_dsc.client_connect(**tup_config.local)

        if args.op == 'get':
            await get_config(*args.param)
        elif args.op == 'set':
            await set_config(*args.param)
        elif args.op == 'del':
            await del_config(*args.param)
        elif args.op == 'clear':
            await clear_config(*args.param)
        elif args.op == 'list':
            await list_config(*args.param)
        else:
            help()
    finally:
        if tup_dsc.client_agent:
            tup_dsc.client_agent.cont = False
            await asyncio.sleep(0.1)
            tup_dsc.client_agent.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    #loop.run_forever()
