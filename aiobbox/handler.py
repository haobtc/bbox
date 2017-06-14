class BaseHandler:
    def add_arguments(self, parser):
        pass

    async def start(self, args):
        pass

    def shutdown(self):
        pass

    async def get_app(self, args):
        raise NotImplemented
