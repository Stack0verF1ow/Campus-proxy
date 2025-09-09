import sys
import os
import socket
import ssl
import select
import http.client
import urllib.parse as urlparse
import threading
import gzip
import zlib
import time
import json
import re
import base64
import configparser
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from io import StringIO, BytesIO
from subprocess import Popen, PIPE
from html.parser import HTMLParser

# 添加新导入
import sqlite3
import win32serviceutil
import win32service
import win32event
import win32api
import requests

# 配置管理
CONFIG_FILE = 'proxy_config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# 数据库初始化
def init_db():
    conn = sqlite3.connect('proxy_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT, token TEXT, permissions TEXT)''')
    conn.commit()
    conn.close()

def with_color(c, s):
    return "\x1b[%dm%s\x1b[0m" % (c, s)


def join_with_script_dir(path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


# 用户认证类
class AuthManager:
    def __init__(self):
        self.failed_attempts = {}
        self.lock = threading.Lock()

    def authenticate(self, auth_header):
        # 实现基本认证和令牌认证
        pass

    def is_allowed(self, user, url):
        # 检查用户是否有权限访问该URL
        pass


# Windows服务封装
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
        # 初始化数据库
        init_db()

        # 启动代理服务器
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        test(HandlerClass=CampusProxyRequestHandler)


# DDNS更新函数
def update_ddns():
    # 获取公网IP并更新DNS记录
    try:
        ip = requests.get('https://api.ipify.org').text
        # 这里使用示例服务，实际替换为您的DDNS提供商API
        requests.get(f"https://ddns.example.com/update?hostname=yourcampusproxy.com&ip={ip}")
    except Exception as e:
        print(f"DDNS update failed: {str(e)}")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def handle_error(self, request, client_address):
        # surpress socket/ssl related errors
        cls, e = sys.exc_info()[:2]
        if cls is socket.error or cls is ssl.SSLError:
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)


class ProxyRequestHandler(BaseHTTPRequestHandler):
    cakey = join_with_script_dir('ca.key')
    cacert = join_with_script_dir('ca.crt')
    certkey = join_with_script_dir('cert.key')
    certdir = join_with_script_dir('certs/')
    timeout = 5
    lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        self.tls = threading.local()
        self.tls.conns = {}

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def log_error(self, format, *args):
        # surpress "Request timed out: timeout('timed out',)"
        if isinstance(args[0], socket.timeout):
            return

        self.log_message(format, *args)

    def do_CONNECT(self):
        if os.path.isfile(self.cakey) and os.path.isfile(self.cacert) and os.path.isfile(
                self.certkey) and os.path.isdir(self.certdir):
            self.connect_intercept()
        else:
            self.connect_relay()

    def connect_intercept(self):
        hostname = self.path.split(':')[0]
        certpath = "%s/%s.crt" % (self.certdir.rstrip('/'), hostname)

        with self.lock:
            if not os.path.isfile(certpath):
                epoch = "%d" % (time.time() * 1000)
                p1 = Popen(["openssl", "req", "-new", "-key", self.certkey, "-subj", "/CN=%s" % hostname], stdout=PIPE)
                p2 = Popen(["openssl", "x509", "-req", "-days", "3650", "-CA", self.cacert, "-CAkey", self.cakey,
                            "-set_serial", epoch, "-out", certpath], stdin=p1.stdout, stderr=PIPE)
                p2.communicate()

        self.wfile.write("%s %d %s\r\n" % (self.protocol_version, 200, 'Connection Established').encode())
        self.end_headers()

        self.connection = ssl.wrap_socket(self.connection, keyfile=self.certkey, certfile=certpath, server_side=True)
        self.rfile = self.connection.makefile("rb", self.rbufsize)
        self.wfile = self.connection.makefile("wb", self.wbufsize)

        conntype = self.headers.get('Proxy-Connection', '')
        if self.protocol_version == "HTTP/1.1" and conntype.lower() != 'close':
            self.close_connection = False
        else:
            self.close_connection = True

    def connect_relay(self):
        address = self.path.split(':', 1)
        address[1] = int(address[1]) or 443
        try:
            s = socket.create_connection(address, timeout=self.timeout)
        except Exception as e:
            self.send_error(502)
            return
        self.send_response(200, 'Connection Established')
        self.end_headers()

        conns = [self.connection, s]
        self.close_connection = False
        while not self.close_connection:
            rlist, wlist, xlist = select.select(conns, [], conns, self.timeout)
            if xlist or not rlist:
                break
            for r in rlist:
                other = conns[1] if r is conns[0] else conns[0]
                data = r.recv(8192)
                if not data:
                    self.close_connection = True
                    break
                other.sendall(data)

    def do_GET(self):
        if self.path == 'http://proxy2.test/':
            self.send_cacert()
            return

        req = self
        content_length = int(req.headers.get('Content-Length', 0))
        req_body = self.rfile.read(content_length) if content_length else None

        if req.path[0] == '/':
            if isinstance(self.connection, ssl.SSLSocket):
                req.path = "https://%s%s" % (req.headers['Host'], req.path)
            else:
                req.path = "http://%s%s" % (req.headers['Host'], req.path)

        req_body_modified = self.request_handler(req, req_body)
        if req_body_modified is False:
            self.send_error(403)
            return
        elif req_body_modified is not None:
            req_body = req_body_modified
            req.headers['Content-length'] = str(len(req_body))

        u = urlparse.urlsplit(req.path)
        scheme, netloc, path = u.scheme, u.netloc, (u.path + '?' + u.query if u.query else u.path)
        assert scheme in ('http', 'https')
        if netloc:
            req.headers['Host'] = netloc
        setattr(req, 'headers', self.filter_headers(req.headers))

        try:
            origin = (scheme, netloc)
            if not origin in self.tls.conns:
                if scheme == 'https':
                    self.tls.conns[origin] = http.client.HTTPSConnection(netloc, timeout=self.timeout)
                else:
                    self.tls.conns[origin] = http.client.HTTPConnection(netloc, timeout=self.timeout)
            conn = self.tls.conns[origin]
            conn.request(self.command, path, req_body, dict(req.headers))
            res = conn.getresponse()

            version_table = {10: 'HTTP/1.0', 11: 'HTTP/1.1'}
            setattr(res, 'headers', res.msg)
            setattr(res, 'response_version', version_table[res.version])

            # support streaming
            if not 'Content-Length' in res.headers and 'no-store' in res.headers.get('Cache-Control', ''):
                self.response_handler(req, req_body, res, '')
                setattr(res, 'headers', self.filter_headers(res.headers))
                self.relay_streaming(res)
                with self.lock:
                    self.save_handler(req, req_body, res, '')
                return

            res_body = res.read()
        except Exception as e:
            if origin in self.tls.conns:
                del self.tls.conns[origin]
            self.send_error(502)
            return

        content_encoding = res.headers.get('Content-Encoding', 'identity')
        res_body_plain = self.decode_content_body(res_body, content_encoding)

        res_body_modified = self.response_handler(req, req_body, res, res_body_plain)
        if res_body_modified is False:
            self.send_error(403)
            return
        elif res_body_modified is not None:
            res_body_plain = res_body_modified
            res_body = self.encode_content_body(res_body_plain, content_encoding)
            res.headers['Content-Length'] = str(len(res_body))

        setattr(res, 'headers', self.filter_headers(res.headers))

        status_line = f"{self.protocol_version} {res.status} {res.reason}\r\n"
        self.wfile.write(status_line.encode())
        for line in res.headers._headers:
            self.wfile.write(line)
        self.end_headers()
        self.wfile.write(res_body)
        self.wfile.flush()

        with self.lock:
            self.save_handler(req, req_body, res, res_body_plain)

    def relay_streaming(self, res):
        status_line = f"{self.protocol_version} {res.status} {res.reason}\r\n"
        self.wfile.write(status_line.encode())
        for line in res.headers._headers:
            self.wfile.write(line)
        self.end_headers()
        try:
            while True:
                chunk = res.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
            self.wfile.flush()
        except socket.error:
            # connection closed by client
            pass

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET

    def filter_headers(self, headers):
        # http://tools.ietf.org/html/rfc2616#section-13.5.1
        hop_by_hop = (
        'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
        'upgrade')
        for k in hop_by_hop:
            if k in headers:
                del headers[k]

        # accept only supported encodings
        if 'Accept-Encoding' in headers:
            ae = headers['Accept-Encoding']
            filtered_encodings = [x for x in re.split(r',\s*', ae) if x in ('identity', 'gzip', 'x-gzip', 'deflate')]
            headers['Accept-Encoding'] = ', '.join(filtered_encodings)

        return headers

    def encode_content_body(self, text, encoding):
        if encoding == 'identity':
            data = text
        elif encoding in ('gzip', 'x-gzip'):
            io = BytesIO()
            with gzip.GzipFile(fileobj=io, mode='wb') as f:
                if isinstance(text, str):
                    text = text.encode('utf-8')
                f.write(text)
            data = io.getvalue()
        elif encoding == 'deflate':
            if isinstance(text, str):
                text = text.encode('utf-8')
            data = zlib.compress(text)
        else:
            raise Exception("Unknown Content-Encoding: %s" % encoding)
        return data

    def decode_content_body(self, data, encoding):
        if encoding == 'identity':
            text = data
        elif encoding in ('gzip', 'x-gzip'):
            io = BytesIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                text = f.read()
        elif encoding == 'deflate':
            try:
                text = zlib.decompress(data)
            except zlib.error:
                text = zlib.decompress(data, -zlib.MAX_WBITS)
        else:
            raise Exception("Unknown Content-Encoding: %s" % encoding)

        if isinstance(text, bytes):
            try:
                text = text.decode('utf-8')
            except UnicodeDecodeError:
                pass
        return text

    def send_cacert(self):
        with open(self.cacert, 'rb') as f:
            data = f.read()

        self.wfile.write("%s %d %s\r\n" % (self.protocol_version, 200, 'OK').encode())
        self.send_header('Content-Type', 'application/x-x509-ca-cert')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)

    def print_info(self, req, req_body, res, res_body):
        def parse_qsl(s):
            return '\n'.join("%-20s %s" % (k, v) for k, v in urlparse.parse_qsl(s, keep_blank_values=True))

        req_header_text = "%s %s %s\n%s" % (req.command, req.path, req.request_version, req.headers)
        res_header_text = "%s %d %s\n%s" % (res.response_version, res.status, res.reason, res.headers)

        print(with_color(33, req_header_text))

        u = urlparse.urlsplit(req.path)
        if u.query:
            query_text = parse_qsl(u.query)
            print(with_color(32, "==== QUERY PARAMETERS ====\n%s\n" % query_text))

        cookie = req.headers.get('Cookie', '')
        if cookie:
            cookie = parse_qsl(re.sub(r';\s*', '&', cookie))
            print(with_color(32, "==== COOKIE ====\n%s\n" % cookie))

        auth = req.headers.get('Authorization', '')
        if auth.lower().startswith('basic'):
            token = auth.split()[1]
            import base64
            token = base64.b64decode(token).decode('utf-8')
            print(with_color(31, "==== BASIC AUTH ====\n%s\n" % token))

        if req_body is not None:
            req_body_text = None
            content_type = req.headers.get('Content-Type', '')

            if content_type.startswith('application/x-www-form-urlencoded'):
                if isinstance(req_body, bytes):
                    req_body = req_body.decode('utf-8')
                req_body_text = parse_qsl(req_body)
            elif content_type.startswith('application/json'):
                try:
                    if isinstance(req_body, bytes):
                        req_body = req_body.decode('utf-8')
                    json_obj = json.loads(req_body)
                    json_str = json.dumps(json_obj, indent=2)
                    if json_str.count('\n') < 50:
                        req_body_text = json_str
                    else:
                        lines = json_str.splitlines()
                        req_body_text = "%s\n(%d lines)" % ('\n'.join(lines[:50]), len(lines))
                except ValueError:
                    req_body_text = req_body
            elif len(req_body) < 1024:
                req_body_text = req_body

            if req_body_text:
                print(with_color(32, "==== REQUEST BODY ====\n%s\n" % req_body_text))

        print(with_color(36, res_header_text))

        cookies = res.headers.get_all('Set-Cookie') if hasattr(res.headers, 'get_all') else res.headers.get(
            'Set-Cookie', [])
        if cookies:
            if isinstance(cookies, str):
                cookies = [cookies]
            cookies = '\n'.join(cookies)
            print(with_color(31, "==== SET-COOKIE ====\n%s\n" % cookies))

        if res_body is not None:
            res_body_text = None
            content_type = res.headers.get('Content-Type', '')

            if content_type.startswith('application/json'):
                try:
                    if isinstance(res_body, bytes):
                        res_body = res_body.decode('utf-8')
                    json_obj = json.loads(res_body)
                    json_str = json.dumps(json_obj, indent=2)
                    if json_str.count('\n') < 50:
                        res_body_text = json_str
                    else:
                        lines = json_str.splitlines()
                        res_body_text = "%s\n(%d lines)" % ('\n'.join(lines[:50]), len(lines))
                except ValueError:
                    res_body_text = res_body
            elif content_type.startswith('text/html'):
                if isinstance(res_body, bytes):
                    res_body_str = res_body.decode('utf-8', errors='ignore')
                else:
                    res_body_str = res_body
                m = re.search(r'<title[^>]*>\s*([^<]+?)\s*</title>', res_body_str, re.I)
                if m:
                    h = HTMLParser()
                    print(with_color(32, "==== HTML TITLE ====\n%s\n" % h.unescape(m.group(1))))
            elif content_type.startswith('text/') and len(res_body) < 1024:
                res_body_text = res_body

            if res_body_text:
                if isinstance(res_body_text, bytes):
                    res_body_text = res_body_text.decode('utf-8', errors='ignore')
                print(with_color(32, "==== RESPONSE BODY ====\n%s\n" % res_body_text))

    def request_handler(self, req, req_body):
        pass

    def response_handler(self, req, req_body, res, res_body):
        pass

    def save_handler(self, req, req_body, res, res_body):
        self.print_info(req, req_body, res, res_body)

# 修改后的代理请求处理类
class CampusProxyRequestHandler(ProxyRequestHandler):
    # 新增配置项
    ADMIN_TOKEN = config.get('security', 'admin_token', fallback='default_token')
    ALLOWED_DOMAINS = json.loads(config.get('access', 'allowed_domains', fallback='[]'))
    MAX_FAILED_ATTEMPTS = config.getint('security', 'max_failed_attempts', fallback=5)
    BLOCK_TIME = config.getint('security', 'block_time', fallback=300)  # 5分钟

    # 初始化认证管理器
    auth_manager = AuthManager()

    def setup(self):
        # 添加客户端IP记录
        self.client_ip = self.client_address[0]
        super().setup()

    def handle_one_request(self):
        # 添加访问频率限制
        if self.is_client_blocked():
            self.send_error(429, "Too Many Requests")
            return
        super().handle_one_request()

    def is_client_blocked(self):
        # 检查客户端是否因多次失败被暂时封禁
        pass

    def do_CONNECT(self):
        # 添加认证检查
        if not self.check_auth():
            self.send_auth_challenge()
            return
        super().do_CONNECT()

    def do_GET(self):
        # 特殊API端点处理
        if self.path.startswith('/proxy-api/'):
            self.handle_api_request()
            return

        # 添加认证检查
        if not self.check_auth():
            self.send_auth_challenge()
            return

        # 添加访问控制
        if not self.is_url_allowed(self.path):
            self.send_error(403, "Forbidden: Access to this resource is restricted")
            return

        super().do_GET()

    # 其他HTTP方法同样需要添加认证和访问控制
    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET

    def check_auth(self):
        # 实现认证逻辑
        auth_header = self.headers.get('Proxy-Authorization', '')
        return self.auth_manager.authenticate(auth_header)

    def send_auth_challenge(self):
        # 发送认证质询
        self.send_response(407)
        self.send_header('Proxy-Authenticate', 'Basic realm="Campus Proxy"')
        self.end_headers()

    def is_url_allowed(self, url):
        # 检查URL是否在允许的校园资源范围内
        domain = urlparse.urlparse(url).netloc.split(':')[0]
        return any(allowed in domain for allowed in self.ALLOWED_DOMAINS)

    def handle_api_request(self):
        # 处理管理API请求
        if self.path == '/proxy-api/config':
            self.handle_config_api()
        elif self.path == '/proxy-api/users':
            self.handle_users_api()
        # 其他API端点...

    def handle_config_api(self):
        # 需要管理员权限
        if not self.is_admin_request():
            self.send_error(403)
            return

        # 返回当前配置
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        config_data = {
            'allowed_domains': self.ALLOWED_DOMAINS,
            'max_connections': config.getint('server', 'max_connections', fallback=100)
        }
        self.wfile.write(json.dumps(config_data).encode())

    def handle_users_api(self):
        # 用户管理API实现
        pass

    def is_admin_request(self):
        # 检查请求是否来自管理员
        return self.headers.get('X-Admin-Token') == self.ADMIN_TOKEN

    def request_handler(self, req, req_body):
        # 移动端优化：压缩请求处理
        if 'mobile' in req.headers.get('User-Agent', '').lower():
            # 特殊处理移动端请求
            pass
        return super().request_handler(req, req_body)

    def response_handler(self, req, req_body, res, res_body):
        # 移动端优化：压缩响应
        if 'mobile' in req.headers.get('User-Agent', '').lower():
            # 添加移动端优化处理
            pass
        return super().response_handler(req, req_body, res, res_body)

    def save_handler(self, req, req_body, res, res_body):
        # 添加审计日志
        self.log_access(req, res)
        super().save_handler(req, req_body, res, res_body)

    def log_access(self, req, res):
        # 记录访问日志到数据库
        log_entry = {
            'timestamp': time.time(),
            'client_ip': self.client_ip,
            'method': req.command,
            'url': req.path,
            'status': res.status,
            'user_agent': req.headers.get('User-Agent', ''),
            'username': self.get_authenticated_user()
        }
        # 保存到数据库或文件
        pass

    def get_authenticated_user(self):
        # 获取当前认证用户
        return "anonymous"  # 实际从认证信息中获取




def test(HandlerClass=CampusProxyRequestHandler, ServerClass=ThreadingHTTPServer, protocol="HTTP/1.1"):
    port = config.getint('server', 'port', fallback=8080)
    server_address = ('::', port)  # 监听所有接口

    # 启用HTTPS
    use_https = config.getboolean('security', 'https', fallback=False)
    certfile = config.get('security', 'certfile', fallback='server.crt')
    keyfile = config.get('security', 'keyfile', fallback='server.key')

    HandlerClass.protocol_version = protocol
    httpd = ServerClass(server_address, HandlerClass)

    if use_https:
        httpd.socket = ssl.wrap_socket(
            httpd.socket,
            certfile=certfile,
            keyfile=keyfile,
            server_side=True
        )

    # 启动DDNS更新线程
    if config.getboolean('network', 'ddns_enabled', fallback=False):
        ddns_thread = threading.Thread(target=ddns_update_loop, daemon=True)
        ddns_thread.start()

    sa = httpd.socket.getsockname()
    print(f"Serving Campus Proxy on {sa[0]} port {sa[1]}...")
    httpd.serve_forever()

# DDNS更新循环
def ddns_update_loop():
    interval = config.getint('network', 'ddns_interval', fallback=3600)  # 1小时
    while True:
        update_ddns()
        time.sleep(interval)


if __name__ == '__main__':
    # 作为Windows服务运行或直接启动
    if len(sys.argv) == 1:
        # 直接运行
        test()
    else:
        win32serviceutil.HandleCommandLine(CampusProxyService)