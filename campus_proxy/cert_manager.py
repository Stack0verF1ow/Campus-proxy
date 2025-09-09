import os
import ssl
import time
from subprocess import Popen, PIPE
from config_manager import ConfigManager

config = ConfigManager()


class CertManager:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.cakey = self.join_script_dir('ca.key')
        self.cacert = self.join_script_dir('ca.crt')
        self.certkey = self.join_script_dir('cert.key')
        self.certdir = self.join_script_dir('certs/')

        # 确保证书目录存在
        os.makedirs(self.certdir, exist_ok=True)

    def join_script_dir(self, path):
        return os.path.join(self.script_dir, path)

    def generate_certificate(self, hostname):
        certpath = os.path.join(self.certdir.rstrip('/'), f"{hostname}.crt")

        # 如果证书已存在且未过期，直接返回
        if os.path.exists(certpath):
            return certpath

        epoch = "%d" % (time.time() * 1000)
        p1 = Popen(["openssl", "req", "-new", "-key", self.certkey,
                    "-subj", f"/CN={hostname}"], stdout=PIPE)
        p2 = Popen(["openssl", "x509", "-req", "-days", "3650",
                    "-CA", self.cacert, "-CAkey", self.cakey,
                    "-set_serial", epoch, "-out", certpath],
                   stdin=p1.stdout, stderr=PIPE)
        p2.communicate()

        return certpath

    def wrap_socket(self, sock):
        return ssl.wrap_socket(
            sock,
            certfile=config.get('security', 'certfile', 'server.crt'),
            keyfile=config.get('security', 'keyfile', 'server.key'),
            server_side=True
        )