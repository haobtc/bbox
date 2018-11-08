from typing import Dict, Any, List, Tuple, Union, Iterable, Set, Optional

HostType = Union[str, Tuple[Tuple[str, int], ...]]

class Result:
    children: List[Result]
    key: str

class Client:
    client_failed: bool

    def __init__(self,
                 host:HostType='127.0.0.1',
                 port:int=2349,
                 protocol:str='http',
                 allow_reconnect:bool=True,
                 allow_redirect:bool=True) -> None: ...
    
    def close(self) -> None: ...
    def write(self, *args, **kw) -> None: ...
    def refresh(self, *args, **kw) -> None: ...
    def delete(self, *args, **kw) -> None: ...

    def read(self, *args, **kw) -> Result: ...


class EtcdConnectionFailed(Exception):
    ...

class EtcdKeyNotFound(Exception):
    ...

class EtcdAlreadyExist(Exception):
    ...
