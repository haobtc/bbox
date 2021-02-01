from distutils.core import setup
from setuptools import find_packages

setup(name='aiobbox',
      version='0.5.6',
      description='multi-lang, highly available rpc framework',
      author='Zeng Ke',
      author_email='zk@bixin.com',
      packages=find_packages(),
      scripts=['bin/bbox.py', 'bin/bbox-gencert'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: MIT',
          'Programming Language :: Python :: 3.6',
          'Operating System :: POSIX',
          'Topic :: Micro-Services',
      ],

      install_requires=[
          'dateutils',
          'aiohttp',
          'aiochannel',
          'websockets',
          'aio_etcd',
          'netifaces',
          'aioredis',
          'etcd3-py',
          'aiocontextvars',
          'sentry-sdk',
      ],
      python_requires='>=3.6',
)
