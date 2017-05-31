from distutils.core import setup

setup(name='aiotup',
      version='0.0.1',
      description='multi-lang, highly available rpc framework',
      author='Zeng Ke',
      author_email='zk@bixin.com',
      packages=['aiotup'],
      package_dir={'aiotup': 'src/aiotup'},
      scripts=['bin/tup'],
      install_requires=['aiohttp',
                        'aiochannel',
                        'websockets']
)
