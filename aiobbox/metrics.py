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
    
        
