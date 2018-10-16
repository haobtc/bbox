class BaseError(Exception):
    pass

class ConnectionError(BaseError):
    pass

class RegisterFailed(BaseError):
    pass

class ETCDError(BaseError):
    pass

class Retry(Exception):
    pass

class Stop(Exception):
    pass

class DataError(BaseError):
    pass

class ServiceError(Exception):
    def __init__(self, code, msg=None):
        self.code = code
        super(ServiceError, self).__init__(msg or code)

