import os, sys
import re
import shlex
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.cluster import get_cluster, get_sharedconfig, SimpleLock
from aiobbox.exceptions import ETCDError
from aiobbox.utils import guess_json, json_pp
from aiobbox.handler import BaseHandler

parser = argparse.ArgumentParser(
    prog='bbox lock',
    description='acquire a lock and execute')

class Handler(BaseHandler):
    help = 'acquire a lock and execute'

    def add_arguments(self, parser):
        parser.add_argument(
            'entry',
            type=str,
            help='lock entry')

        parser.add_argument(
            'commands',
            type=str,
            nargs='*',
            help='command after the lock is acquired')

    async def run(self, args):
        try:
            await get_cluster().start()
        except ETCDError:
            return

        c = get_cluster()
        async with c.acquire_lock(args.entry) as lock:
            if lock.is_acquired and args.commands:
                proc = await asyncio.create_subprocess_shell(
                    ' '.join(shlex.quote(a)
                             for a in args.commands))
                await proc.communicate()
            else:
                await asyncio.sleep(0.1)

    def shutdown(self):
        loop = asyncio.get_event_loop()
        c = get_cluster()
        loop.run_until_complete(SimpleLock.close_all_keys(c))
        c.cont = False
        c.close()
