import logging
import asyncio

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
        task = asyncio.create_task(asyncio.sleep(secs))
        self._sleep_tasks.append(task)
        try:
            return await task
        except asyncio.CancelledError:
            logging.info('handler %s been cancelled', self)
        finally:
            try:
                self._sleep_tasks.remove(task)
            except ValueError:
                # in case task is not in sleep_tasks
                pass

    def awake(self):
        for task in self._sleep_tasks:
            task.cancel()
