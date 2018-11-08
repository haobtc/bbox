from typing import Dict, Any, List, Tuple, Union, Iterable, Optional
from collections import defaultdict
from aiobbox.metrics import add_metrics, IMetricsEntry, MEntry

class RPCRequestCount(IMetricsEntry):
    def __init__(self, name:str, help:str=''):
        self.name = name
        if not help:
            self.help = self.name.replace('_', ' ')
        else:
            self.help = help
        self.values: Dict[str, float] = defaultdict(float)

    def incr(self, endpoint:str, v:float=1) -> None:
        self.values[endpoint] += v

    def setv(self, endpoint:str, v:float):
        self.values[endpoint] = v

    async def collect(self) -> List[MEntry]:
        arr:List[MEntry] = [({'endpoint': k}, v)
               for k, v in self.values.items()]
        # clear old value
        self.values = defaultdict(int)
        return arr

rpc_request_count = RPCRequestCount(
    'rpc_requests',
    help='RPC request count since last time')
add_metrics(rpc_request_count)

slow_rpc_request_count = RPCRequestCount(
    'slow_rpc_requests',
    help='Slow RPC request count since last time')
add_metrics(slow_rpc_request_count)

error_rpc_request_count = RPCRequestCount(
    'error_rpc_requests',
    help='Error RPC request count since last time')
add_metrics(error_rpc_request_count)
