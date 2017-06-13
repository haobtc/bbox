from distutils.core import setup

setup(name='aiobbox',
      version='0.0.1',
      description='multi-lang, highly available rpc framework',
      author='Zeng Ke',
      author_email='zk@bixin.com',
      packages=['aiobbox'],
      package_dir={'aiobbox': 'aiobbox'},
      scripts=['bin/bbox'],
      install_requires=[
          'aiohttp',
          'aiochannel',
          'websockets',
          'aio_etcd',
          'netifaces'
      ]
)
