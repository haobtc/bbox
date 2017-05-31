import os, sys
import json
import argparse
from aiotup import config

parser = argparse.ArgumentParser(
    description='start tup python project')

parser.add_argument(
    'key',
    type=str,
    help='print key')

def main():
    args = parser.parse_args()    
    config.parse_local()
    try:
        print(config.local[args.key])
    except KeyError:
        # Failed to find the key
        sys.exit(1)
        
if __name__ == '__main__':
    main()
