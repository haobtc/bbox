import os

if os.getenv('BBOX_ETCD_V3', '') in ('1', 'yes'):
    from .etcd3_client import EtcdClient
else:
    from .etcd2_client import EtcdClient
