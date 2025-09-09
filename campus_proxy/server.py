import sys
import threading
import socket
import time
import requests
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from config_manager import ConfigManager
from proxy_handler import ProxyRequestHandler

config = ConfigManager()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def handle_error(self, request, client_address):
        # 错误处理
        pass


def update_ddns():
    try:
        ip = requests.get('https://api.ipify.org').text
        # 实际使用中替换为您的DDNS提供商API
        requests.get(f"https://ddns.example.com/update?hostname=yourcampusproxy.com&ip={ip}")
    except Exception as e:
        print(f"DDNS update failed: {str(e)}")


def ddns_update_loop():
    interval = config.getint('network', 'ddns_interval', 3600)
    while True:
        update_ddns()
        time.sleep(interval)


def start_server():
    port = config.getint('server', 'port', 8080)
    bind_address = config.get('server', 'bind_address', '::')

    server_address = (bind_address, port)
    httpd = ThreadingHTTPServer(server_address, ProxyRequestHandler)

    # 启用HTTPS
    if config.getboolean('security', 'https', False):
        from cert_manager import CertManager
        cert_manager = CertManager()
        httpd.socket = cert_manager.wrap_socket(httpd.socket)

    # 启动DDNS更新线程
    if config.getboolean('network', 'ddns_enabled', False):
        ddns_thread = threading.Thread(target=ddns_update_loop, daemon=True)
        ddns_thread.start()

    print(f"Starting campus proxy server on {bind_address}:{port}...")
    print(f"Security: HTTPS {'enabled' if config.getboolean('security', 'https') else 'disabled'}")
    print(f"Authentication: {'enabled' if config.getboolean('security', 'require_auth') else 'disabled'}")
    print(f"Allowed domains: {config.get('access', 'allowed_domains')}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")