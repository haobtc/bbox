if True:
    from .etcd2_client import EtcdClient
else:
    from .etcd3_client import EtcdClient
