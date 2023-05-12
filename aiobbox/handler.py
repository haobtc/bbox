from typing import Dict, Any, List, Union, Iterable, Set, Coroutine
import logging
from argparse import Namespace, ArgumentParser
import asyncio
from aiobbox.utils import sleep

class BaseHandler:
    cont: bool = True
    help: str = ''

    def __init__(self):
        self._sleep_tasks = []

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    async def start(self, args: Namespace) -> None:
        pass

    def shutdown(self) -> Union[None, Coroutine[Any, Any, None]]:
        pass

    async def get_app(self, args: Namespace) -> Any:
        '''
        Called by starthttpd
        '''
        raise NotImplemented

    async def run(self, args: Namespace) -> None:
        '''
        Called by runtask
        '''
        raise NotImplemented

    async def sleep(self, secs: float) -> Any:
        return await sleep(secs)
