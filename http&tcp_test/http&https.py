import threading
import socket
import requests
import ssl
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.core.window import Window


class NetworkClient:
    def __init__(self):
        self.callback = None

    def set_callback(self, callback):
        """设置UI更新回调函数"""
        self.callback = callback

    def http_get(self, url):
        """发送HTTP GET请求"""
        try:
            response = requests.get(url, timeout=5)
            return response.text
        except Exception as e:
            return f"HTTP Error: {str(e)}"

    def http_post(self, url, data):
        """发送HTTP POST请求"""
        try:
            response = requests.post(url, data=data, timeout=5)
            return response.text
        except Exception as e:
            return f"HTTP Error: {str(e)}"

    def https_cert_test(self, url):
        """测试HTTPS证书信息"""
        try:
            # 解析URL获取主机名
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or 443

            # 创建SSL上下文
            context = ssl.create_default_context()
            context.check_hostname = True

            # 创建socket连接
            with socket.create_connection((hostname, port)) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    # 获取证书信息
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()

                    # 获取证书路径
                    der_cert = ssock.getpeercert(binary_form=True)
                    pem_cert = ssl.DER_cert_to_PEM_cert(der_cert)

                    # 组织结果信息
                    result = f"HTTPS Certificate Test for {hostname}:\n"
                    result += f"Encryption: {cipher[0]} (bits: {cipher[2]})\n\n"
                    result += "Certificate Details:\n"

                    # 添加主题信息
                    subject = dict(x[0] for x in cert['subject'])
                    result += f"  Subject: {subject}\n"

                    # 添加颁发者信息
                    issuer = dict(x[0] for x in cert['issuer'])
                    result += f"  Issuer: {issuer}\n"

                    # 添加有效期信息
                    result += f"  Valid From: {cert['notBefore']}\n"
                    result += f"  Valid Until: {cert['notAfter']}\n"

                    # 添加证书路径
                    result += "\nCertificate Path (PEM format):\n"
                    result += pem_cert

                    return result
        except Exception as e:
            return f"HTTPS Certificate Test Error: {str(e)}"


class NetworkApp(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.network_client = NetworkClient()
        self.network_client.set_callback(self.update_log)

        # 创建HTTP选项卡
        http_tab = TabbedPanelItem(text='HTTP')
        http_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.http_url = TextInput(text='http://httpbin.org/get', size_hint_y=None, height=40)
        self.http_data = TextInput(text='Sample data', size_hint_y=None, height=40)
        self.http_log = TextInput(readonly=True, size_hint_y=0.7)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_get = Button(text='GET', on_press=self.send_http_get)
        btn_post = Button(text='POST', on_press=self.send_http_post)
        btn_layout.add_widget(btn_get)
        btn_layout.add_widget(btn_post)

        http_layout.add_widget(Label(text='URL:', size_hint_y=None, height=30))
        http_layout.add_widget(self.http_url)
        http_layout.add_widget(Label(text='Data (for POST):', size_hint_y=None, height=30))
        http_layout.add_widget(self.http_data)
        http_layout.add_widget(btn_layout)
        http_layout.add_widget(Label(text='Response:', size_hint_y=None, height=30))
        http_layout.add_widget(self.http_log)

        http_tab.add_widget(http_layout)
        self.add_widget(http_tab)

        # 创建HTTPS证书测试选项卡
        https_tab = TabbedPanelItem(text='HTTPS Cert')
        https_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.https_url = TextInput(text='https://example.com', size_hint_y=None, height=40)
        self.https_log = TextInput(readonly=True, size_hint_y=0.8)

        https_btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_test = Button(text='Test Certificate', on_press=self.test_https_cert)
        https_btn_layout.add_widget(btn_test)

        https_layout.add_widget(Label(text='URL:', size_hint_y=None, height=30))
        https_layout.add_widget(self.https_url)
        https_layout.add_widget(https_btn_layout)
        https_layout.add_widget(Label(text='Certificate Details:', size_hint_y=None, height=30))
        https_layout.add_widget(self.https_log)

        https_tab.add_widget(https_layout)
        self.add_widget(https_tab)

    def update_log(self, message):
        """更新日志显示"""
        if self.current_tab.text == 'HTTP':
            self.http_log.text += f"{message}\n"
        elif self.current_tab.text == 'HTTPS Cert':
            self.https_log.text += f"{message}\n"

    def send_http_get(self, instance):
        """发送HTTP GET请求"""
        url = self.http_url.text
        result = self.network_client.http_get(url)
        self.update_log(f"GET {url}\n{result}")

    def send_http_post(self, instance):
        """发送HTTP POST请求"""
        url = self.http_url.text
        data = self.http_data.text
        result = self.network_client.http_post(url, data)
        self.update_log(f"POST {url}\nData: {data}\n{result}")

    def test_https_cert(self, instance):
        """测试HTTPS证书"""
        url = self.https_url.text
        result = self.network_client.https_cert_test(url)
        self.update_log(result)


class NetworkDemoApp(App):
    def build(self):
        Window.size = (600, 600)
        return NetworkApp()


if __name__ == '__main__':
    NetworkDemoApp().run()