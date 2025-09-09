import time
import json
import logging
from config_manager import ConfigManager

config = ConfigManager()


class LoggingManager:
    def __init__(self):
        self.access_logger = self.setup_logger('access', config.get('logging', 'access_log', 'access.log'))
        self.error_logger = self.setup_logger('error', config.get('logging', 'error_log', 'error.log'))

    def setup_logger(self, name, log_file):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def log_access(self, client_ip, method, url, status, user_agent, username):
        log_data = {
            'timestamp': time.time(),
            'client_ip': client_ip,
            'method': method,
            'url': url,
            'status': status,
            'user_agent': user_agent,
            'username': username
        }
        self.access_logger.info(json.dumps(log_data))

    def log_error(self, message):
        self.error_logger.error(message)