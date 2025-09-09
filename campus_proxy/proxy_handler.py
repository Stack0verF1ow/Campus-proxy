import socket
import ssl
import select
import http.client
import urllib.parse as urlparse
import threading
import os
import gzip
import zlib
import time
import json
import re
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from subprocess import Popen, PIPE
from html.parser import HTMLParser

from config_manager import ConfigManager
from auth_manager import AuthManager
from cert_manager import CertManager
from logging_manager import LoggingManager

config = ConfigManager()
auth_manager = AuthManager()
cert_manager = CertManager()
logger = LoggingManager()


class ProxyRequestHandler(BaseHTTPRequestHandler):
    timeout = config.getint('server', 'timeout', 5)
    lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        self.tls = threading.local()
        self.tls.conns = {}
        super().__init__(*args, **kwargs)

    def setup(self):
        self.client_ip = self.client_address[0]
        super().setup()

    def handle_one_request(self):
        if auth_manager.is_client_blocked(self.client_ip):
            self.send_error(429, "Too Many Requests")
            return
        super().handle_one_request()

    def do_CONNECT(self):
        if not self.check_auth():
            self.send_auth_challenge()
            return

        if os.path.isfile(cert_manager.cakey) and os.path.isfile(cert_manager.cacert):
            self.connect_intercept()
        else:
            self.connect_relay()

    def connect_intercept(self):
        hostname = self.path.split(':')[0]
        certpath = cert_manager.generate_certificate(hostname)

        self.wfile.write(f"{self.protocol_version} 200 Connection Established\r\n".encode())
        self.end_headers()

        self.connection = ssl.wrap_socket(self.connection, keyfile=cert_manager.certkey,
                                          certfile=certpath, server_side=True)
        self.rfile = self.connection.makefile("rb", self.rbufsize)
        self.wfile = self.connection.makefile("wb", self.wbufsize)

        self.set_connection_keepalive()

    def connect_relay(self):
        # 中继模式实现
        pass

    def do_GET(self):
        if self.path == 'http://proxy2.test/':
            self.send_cacert()
            return

        if not self.check_auth():
            self.send_auth_challenge()
            return

        # 其他GET请求处理
        pass

    # 其他HTTP方法
    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET

    def check_auth(self):
        if not config.getboolean('security', 'require_auth', True):
            return True

        auth_header = self.headers.get('Proxy-Authorization', '')
        authenticated = auth_manager.authenticate(auth_header)

        if not authenticated:
            auth_manager.record_failed_attempt(self.client_ip)

        return authenticated

    def send_auth_challenge(self):
        self.send_response(407)
        self.send_header('Proxy-Authenticate', 'Basic realm="Campus Proxy"')
        self.end_headers()

    def set_connection_keepalive(self):
        conntype = self.headers.get('Proxy-Connection', '')
        if self.protocol_version == "HTTP/1.1" and conntype.lower() != 'close':
            self.close_connection = False
        else:
            self.close_connection = True

    def send_cacert(self):
        with open(cert_manager.cacert, 'rb') as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'application/x-x509-ca-cert')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)

    def log_access(self, req, res):
        logger.log_access(
            self.client_ip,
            req.command,
            req.path,
            res.status,
            req.headers.get('User-Agent', ''),
            self.get_authenticated_user()
        )

    def get_authenticated_user(self):
        # 从认证信息中获取用户名
        return "unknown"