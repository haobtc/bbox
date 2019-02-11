from typing import Dict, Any, List, Union, Iterable, Set, Optional, Awaitable
import ssl

class ClientError(Exception):
    ...

class ClientConnectorError(Exception):
    ...

class ClientConnectionError(Exception):
    ...

class Request:
    headers: Dict[str, str]

class Response:
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type:Any, exc:Any, tb:Any): ...
    async def json(self) -> Dict[str, Any]: ...

class TCPConnector:
    def __init__(self, ssl_context:Optional[ssl.SSLContext]=None) -> None:
        ...

class ClientSession:
    def __init__(self, connector:Optional[TCPConnector]=None) -> None:
        ...

    def post(self, url:str,
             headers:Optional[Dict[str, Any]]=None,
             json:Any=None,
             timeout:Optional[float]=None) -> Response:
        ...

    def get(self, url:str,
            headers:Optional[Dict[str, Any]]=None,
            timeout:Optional[float]=None) -> Response:
        ...

