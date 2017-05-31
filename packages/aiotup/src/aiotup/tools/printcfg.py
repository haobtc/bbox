import os, sys
import json
import argparse
from aiotup.config import Config

parser = argparse.ArgumentParser(
    description='start tup python project')

parser.add_argument(
    'key',
    type=str,
    help='print key')

def main():
    args = parser.parse_args()    
    config = Config.parse()
    try:
        print(config[args.key])
    except KeyError:
        # Failed to find the key
        sys.exit(1)
        
if __name__ == '__main__':
    main()
