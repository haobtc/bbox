from typing import Dict, Any, List, Tuple, Union, Iterable, Optional
import asyncio
from collections import defaultdict
from aiobbox.cluster import get_cluster

MEntry = Tuple[Dict[str, Any], float]

class IMetricsEntry:
    name: str = ''
    help: str = ''
    type: str = 'gauge'
    field_name: str = ''

    async def collect(self) -> List[MEntry]:
        raise NotImplemented

_metrics: List[IMetricsEntry] = []

def add_metrics(entry:IMetricsEntry) -> None:
    assert getattr(entry, 'name', None)
    assert getattr(entry, 'help', None)
    assert getattr(entry, 'type', None)
    #assert hasattr(entry, 'collect')
    _metrics.append(entry)

async def collect_metrics():
    results = await asyncio.gather(
        *[entry.collect() for entry in _metrics])

    meta = {}
    lines = []
    for entry, res in zip(_metrics, results):
        meta[entry.name] = {
            'help': entry.help,
            'type': entry.type
        }
        for labels, v in res:
            lines.append((entry.name, labels, v))
    return {
        'meta': meta,
        'lines': lines
        }

def collect_cluster_metrics() -> Dict[str, Any]:
    cluster = get_cluster()
    meta = {
        'service_boxes': {
            'type': 'gauge',
            'help': 'The count of boxes for each service'
            }
        }

    lines = []
    for srv_name, boxes in cluster.route.items():
        lines.append(
            ('service_boxes',
             {'srv': srv_name},
             len(boxes)))
    return {
        'meta': meta,
        'lines': lines
        }

def report_box_failure(bind:str) -> Dict[str, Any]:
    meta = {
        'box_fail': {
            'type': 'gauge',
            'help': 'box cannot connect'
            }
        }
    c = get_cluster()
    box = c.boxes.get(bind)
    labels = {'bind': bind}
    if box:
        labels['box'] = box['boxid']
    lines = [('box_fail', labels, 1)]
    return {
        'meta': meta,
        'lines': lines
        }

class MetricsCount(IMetricsEntry):
    values:Dict[str, float] = defaultdict(int)

    def incr(self, coin:str) -> None:
        self.values[coin] += 1

    async def collect(self) -> List[MEntry]:
        metr: List[MEntry] = []
        for coin, cnt in self.values.items():
            mentry: MEntry = ({self.field_name: coin}, cnt)
            metr.append(mentry)
        self.values.clear()
        return metr

class MetricsAmount(IMetricsEntry):
    values:Dict[str, float] = defaultdict(float)
    def add(self, key:str, amount:float) -> None:
        self.values[key] += amount

    async def collect(self) -> List[MEntry]:
        metr = []
        for key, cnt in self.values.items():
            metr.append(({self.field_name: key}, cnt))
        self.values.clear()
        return metr
