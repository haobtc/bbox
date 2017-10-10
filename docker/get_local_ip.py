import sys
from aiobbox.utils import  get_localbox_ipset

def main():
    ipset = get_localbox_ipset()
    for ip in ipset:
        if ip != '127.0.0.1':
            print(ip)
            sys.exit()

if __name__ == '__main__':
    main()
