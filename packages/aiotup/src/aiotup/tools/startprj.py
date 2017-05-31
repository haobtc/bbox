import os, sys
import json
import asyncio
import argparse
import aiotup.server as tup_server
import aiotup.config as config

parser = argparse.ArgumentParser(
    description='start tup python project')

parser.add_argument(
    'module',
    type=str,
    nargs='+',
    help='the tup sevice module to load')

parser.add_argument(
    '--bind',
    type=str,
    default='localhost:8080',
    help='server host')

def main():
    config.parse_local()
    if config.local.language != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    for mod in args.module:
        __import__(mod)

    #host, port = args.bind.split(':')
    loop = asyncio.get_event_loop()

    r = tup_server.http_server(loop)
    srv, handler = loop.run_until_complete(r)
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(handler.finish_connections())
        pass


if __name__ == '__main__':
    main()
