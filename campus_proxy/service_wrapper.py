import win32serviceutil
import win32service
import win32event
import win32api
import servicemanager
import socket
import sys

from server import start_server


class CampusProxyService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'CampusProxy'
    _svc_display_name_ = '校园代理服务'
    _svc_description_ = '提供通过公网访问校园内网资源的代理服务'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # 在单独的线程中运行代理服务器
        import threading
        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True
        server_thread.start()

        # 等待停止事件
        while self.is_alive:
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                break