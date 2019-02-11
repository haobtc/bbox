from typing import Dict, Any, List, Union, Iterable, Set, Optional, Callable

class Response:
    def __init__(self, data:Optional[str]=None):
        pass

class HTTPBadRequest(Response):
    ...

class HTTPNotFound(Response):
    ...

class HTTPBadGateway(Response):
    ...

def json_response(data:Dict[str, Any]) -> Response:
    ...

class Router:
    def add_post(self, path:str, Callable) -> None: ...

class Application:
    router: Router
    def make_handler(self) -> Callable: ...

