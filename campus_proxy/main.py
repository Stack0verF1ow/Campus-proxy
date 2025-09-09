import sys
from service_wrapper import CampusProxyService
import win32serviceutil

if __name__ == '__main__':
    if len(sys.argv) == 1:
        from server import start_server
        start_server()
    else:
        win32serviceutil.HandleCommandLine(CampusProxyService)