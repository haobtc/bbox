import os, sys
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
import aiobbox.config as bbox_config
import aiobbox.discovery as bbox_dsc

parser = argparse.ArgumentParser(
    description='start bbox python project')

parser.add_argument(
    'module',
    type=str,
    nargs='+',
    help='the bbox sevice module to load')

parser.add_argument(
    '--bind',
    type=str,
    default='localhost:8080',
    help='server host')

def main():
    bbox_config.parse_local()
    if bbox_config.local['language'] != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    for mod in args.module:
        __import__(mod)

    #host, port = args.bind.split(':')
    loop = asyncio.get_event_loop()

    r = bbox_server.http_server(loop)
    srv, handler = loop.run_until_complete(r)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        if bbox_dsc.server_agent:
            loop.run_until_complete(bbox_dsc.server_agent.deregister())
        loop.run_until_complete(handler.finish_connections())


if __name__ == '__main__':
    main()
