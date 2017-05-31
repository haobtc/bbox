import sys
import aiotup.server as tup_server

def main():
    for mod in sys.argv[1:]:
        __import__(mod)
        
    tup_server.webapp()

if __name__ == '__main__':
    main()
        

