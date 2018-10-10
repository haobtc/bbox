class BaseHandler:
    cont = True
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
