import logging
import asyncio
from aiobbox.utils import sleep

class BaseHandler:
    cont = True
    def __init__(self):
        self._sleep_tasks = []

    def add_arguments(self, parser):
        pass

    async def start(self, args):
        pass

    def shutdown(self):
        pass

    async def get_app(self, args):
        '''
        Called by starthttpd
        '''
        raise NotImplemented

    async def run(self, args):
        '''
        Called by runtask
        '''
        raise NotImplemented

    async def sleep(self, secs):
        return await sleep(secs)
