import os, sys
import re
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.cluster import get_cluster, get_sharedconfig
from aiobbox.utils import guess_json, json_pp

async def get_config():
    parser = argparse.ArgumentParser(
        prog='bbox config get',
        description='get config')

    parser.add_argument(
        'sec_key',
        type=str,
        help='sec/key or sec')

    args = parser.parse_args(sys.argv[2:])
    sec_key = args.sec_key
    
    if '/' in sec_key:
        sec, key = sec_key.split('/')
        r = get_sharedconfig().get_strict(sec, key)
    else:
        r = get_sharedconfig().get_section_strict(sec_key)
    print(json_pp(r))

async def set_config():
    parser = argparse.ArgumentParser(
        prog='bbox config set',
        description='set config value')

    parser.add_argument(
        'sec_key',
        type=str,
        help='sec/key or sec')

    parser.add_argument(
        'value',
        type=str,
        help='value')
    
    args = parser.parse_args(sys.argv[2:])

    sec, key = args.sec_key.split('/')
    value = guess_json(args.value)
    return await get_cluster().set_config(sec, key, value)

async def del_config():
    parser = argparse.ArgumentParser(
        prog='bbox config del',
        description='delete config')

    parser.add_argument(
        'sec_key',
        type=str,
        help='sec/key or sec')
    args = parser.parse_args(sys.argv[2:])
    sec_key = args.sec_key
    
    if '/' in sec_key:
        sec, key = sec_key.split('/')
        return await get_cluster().del_config(sec, key)
    else:
        return await get_cluster().del_section(sec_key)

async def clear_config():
    return await get_cluster().clear_config()

async def dump_config():
    data = get_sharedconfig().dump_json()
    print(data)

async def load_config():
    parser = argparse.ArgumentParser(
        prog='bbox config load',
        description='delete config')

    parser.add_argument(
        'jsonfile',
        type=str,
        help='config file in json format')

    parser.add_argument(
        '--purge',
        type=bool,
        default=False,
        help='delete old config items different from the local file')
    args = parser.parse_args(sys.argv[2:])
    jsonfile = args.jsonfile
    
    with open(jsonfile, 'r', encoding='utf-8') as f:
        new_sections = json.load(f)
    rem_set, add_set = get_sharedconfig().compare_sections(
        new_sections)
    if not args.merge:
        for sec, key, value in rem_set:
            print("delete", sec, key)
            await get_cluster().del_config(sec, key)

    for sec, key, value in add_set:
        value = json.loads(value)
        print("set", sec, key)
        await get_cluster().set_config(sec, key, value)

def help(f=sys.stdout):
    print('Commands', file=f)
    print(' get sec.key|sec  - get config or section', file=f)
    print(' set sec.key value  - set config', file=f)
    print(' dump  - dump configs in json format', file=f)
    print(' del sec.key|sec  - delete config or section', file=f)
    print(' clear  - clear configs', file=f)
    print(' load config.json  - clear configs', file=f)

async def main():
    if len(sys.argv) <= 1:
        print('unknown command', file=sys.stderr)
        help(f=sys.stderr)
        sys.exit(1)
    try:
        command = sys.argv[1]
        await get_cluster().start()
        if command == 'get':
            await get_config()
        elif command == 'set':
            await set_config()
        elif command == 'del':
            await del_config()
        elif command == 'clear':
            await clear_config()
        elif command in ('dump', 'list'):
            await dump_config()
        elif command == 'load':
            await load_config()
        else:
            help()
    finally:
        c = get_cluster()
        c.cont = False
        await asyncio.sleep(0.1)
        c.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
