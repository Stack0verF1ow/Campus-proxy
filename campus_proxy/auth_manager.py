import base64
import sqlite3
import threading
import time
from config_manager import ConfigManager

config = ConfigManager()


class AuthManager:
    def __init__(self):
        self.failed_attempts = {}
        self.lock = threading.Lock()
        self.db_path = 'proxy_users.db'
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY, username TEXT, password TEXT, token TEXT, permissions TEXT)''')
        conn.commit()
        conn.close()

    def authenticate(self, auth_header):
        if config.getboolean('security', 'test_mode', fallback=False):
            return True

        if not auth_header:
            return False

        if auth_header.startswith('Basic '):
            return self.authenticate_basic(auth_header[6:])
        elif auth_header.startswith('Bearer '):
            return self.authenticate_token(auth_header[7:])
        return False

    def authenticate_basic(self, token):
        try:
            credentials = base64.b64decode(token).decode('utf-8')
            username, password = credentials.split(':', 1)
            return self.check_db_credentials(username, password)
        except:
            return False

    def authenticate_token(self, token):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE token=?", (token,))
        user = c.fetchone()
        conn.close()
        return user is not None

    def check_db_credentials(self, username, password):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        return user is not None

    def is_client_blocked(self, client_ip):
        with self.lock:
            now = time.time()
            attempts = self.failed_attempts.get(client_ip, [])

            # 移除过期的失败尝试
            recent_attempts = [t for t in attempts if now - t < config.getint('security', 'block_time', 300)]

            # 检查是否超过最大失败尝试次数
            if len(recent_attempts) >= config.getint('security', 'max_failed_attempts', 5):
                return True

            # 更新失败尝试记录
            self.failed_attempts[client_ip] = recent_attempts
            return False

    def record_failed_attempt(self, client_ip):
        with self.lock:
            now = time.time()
            attempts = self.failed_attempts.get(client_ip, [])
            attempts.append(now)
            self.failed_attempts[client_ip] = attempts