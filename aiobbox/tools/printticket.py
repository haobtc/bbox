import os, sys
import json
import argparse
from aiobbox.cluster import get_ticket
from aiobbox.log import config_log

config_log(mute_console=True)

parser = argparse.ArgumentParser(
    description='start bbox python project')

parser.add_argument(
    'key',
    type=str,
    help='print key')

def main():
    args = parser.parse_args()
    try:
        print(get_ticket()[args.key])
    except KeyError:
        # Failed to find the key
        sys.exit(1)
        
if __name__ == '__main__':
    main()
