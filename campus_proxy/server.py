import threading
import socket
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from config_manager import ConfigManager
from proxy_handler import ProxyRequestHandler

config = ConfigManager()

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET
    daemon_threads = True

    def handle_error(self, request, client_address):
        # 错误处理
        pass

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

    print(f"Starting campus proxy server on {bind_address}:{port}...")
    print(f"Security: HTTPS {'enabled' if config.getboolean('security', 'https') else 'disabled'}")
    print(f"Authentication: {'enabled' if config.getboolean('security', 'require_auth') else 'disabled'}")
    print(f"Allowed domains: {config.get('access', 'allowed_domains')}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")