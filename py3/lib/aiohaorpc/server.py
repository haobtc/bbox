from functools import wraps

srv_dict = {}

class Service(object):
    def __init__(self, srv_name):
        self.srv_name = srv_name
        self.methods = {}
        srv_dict[srv_name] = self

    def method(self, name):
        def decorator(fn):
            __w = wraps(fn)(fn)
            self.methods[name] = __w
            return __w
        return decorator

