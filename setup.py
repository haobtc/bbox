from distutils.core import setup


setup(name='aiobbox',
      version='0.0.1',
      description='multi-lang, highly available rpc framework',
      author='Zeng Ke',
      author_email='zk@bixin.com',
      packages=[
          'aiobbox',
          'aibbox.tools',
          'aiobbox.cluster',
          'aiobbox.services',
          'aiobbox.contrib.consumer',
      ],
      package_dir={
          'aiobbox': 'aiobbox',
          'aiobbox.tools': 'aiobbox/tools',
          'aiobbox.services': 'aiobbox/services',
          'aiobbox.cluster': 'aiobbox/cluster',
          'aiobbox.contrib.consumer': 'aiobbox/contrib/consumer'
      },
      scripts=['bin/bbox'],
      install_requires=[
          'aiohttp',
          'aiochannel',
          'websockets',
          'aio_etcd',
          'netifaces'
      ]
)
