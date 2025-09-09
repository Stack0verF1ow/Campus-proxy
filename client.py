from kivymd.app import MDApp
from kivy.network.urlrequest import UrlRequest


class ProxyTestApp(MDApp):
    def build(self):
        self.test_proxy()

    def test_proxy(self):
        proxy = {
            'http': 'http://admin:securepassword@YOUR_SERVER_IP:8081',
            'https': 'http://admin:securepassword@YOUR_SERVER_IP:8081'
        }

        UrlRequest(
            'http://httpbin.org/get',
            on_success=self.handle_success,
            on_error=self.handle_error,
            req_headers={'User-Agent': 'KivyMD Proxy Test'},
            proxy=proxy
        )

    def handle_success(self, req, result):
        print("Proxy test successful!")
        print(result)

    def handle_error(self, req, error):
        print("Proxy test failed:", error)


if __name__ == '__main__':
    ProxyTestApp().run()