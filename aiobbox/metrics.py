import asyncio
from collections import defaultdict
from aiobbox.cluster import get_cluster

_metrics = []

def add_metrics(obj):
    assert getattr(obj, 'name', None)
    assert getattr(obj, 'help', None)
    assert getattr(obj, 'type', None)
    assert hasattr(obj, 'collect')
    _metrics.append(obj)

async def collect_metrics():
    results = await asyncio.gather(
        *[obj.collect() for obj in _metrics])

    meta = {}
    lines = []
    for obj, res in zip(_metrics, results):
        meta[obj.name] = {
            'help': obj.help,
            'type': obj.type
        }
        for labels, v in res:
            lines.append((obj.name, labels, v))
    return {
        'meta': meta,
        'lines': lines
        }

def collect_cluster_metrics():
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

def report_box_failure(bind):
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

class MetricsCount:
    name = None
    help = None
    field_name = None
    type = 'gauge'

    values = defaultdict(int)
    def incr(self, coin):
        self.values[coin] += 1

    async def collect(self):
        metr = []
        for coin, cnt in self.values.items():
            metr.append(({self.field_name: coin}, cnt))
        self.values.clear()
        return metr

class MetricsAmount:
    name = None
    help = None
    field_name = None
    type = 'gauge'

    values = defaultdict(float)
    def add(self, key, amount):
        self.values[key] += amount

    async def collect(self):
        metr = []
        for key, cnt in self.values.items():
            metr.append(({self.field_name: key}, cnt))
        self.values.clear()
        return metr
