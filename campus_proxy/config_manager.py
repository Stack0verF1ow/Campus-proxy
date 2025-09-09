import configparser
import os


class ConfigManager:
    def __init__(self, config_file='proxy_config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.create_default_config()
        self.config.read(self.config_file)

    def create_default_config(self):
        self.config['server'] = {
            'port': '8080',
            'max_connections': '100',
            'bind_address': '::'
        }
        self.config['security'] = {
            'https': 'false',
            'certfile': 'server.crt',
            'keyfile': 'server.key',
            'admin_token': 'default_token',
            'max_failed_attempts': '5',
            'block_time': '300',
            'require_auth': 'false',
            'test_mode': 'true'
        }
        self.config['access'] = {
            'allowed_domains': '["campus.edu", "library.edu"]'
        }
        self.config['network'] = {
            'ddns_enabled': 'false',
            'ddns_interval': '3600'
        }
        self.config['logging'] = {
            'access_log': 'access.log',
            'error_log': 'error.log'
        }

        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def get(self, section, option, fallback=None):
        return self.config.get(section, option, fallback=fallback)

    def getint(self, section, option, fallback=0):
        return self.config.getint(section, option, fallback=fallback)

    def getboolean(self, section, option, fallback=False):
        return self.config.getboolean(section, option, fallback=fallback)

    def getlist(self, section, option, fallback=[]):
        value = self.get(section, option, None)
        if value is None:
            return fallback
        return eval(value)  # 注意：实际使用中应考虑更安全的方式