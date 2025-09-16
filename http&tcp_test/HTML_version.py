import re
import threading
import socket
import requests
from html.parser import HTMLParser
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import AsyncImage
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.core.text import LabelBase
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
from bs4 import BeautifulSoup


# 自定义 HTML 解析器
class HTMLRenderer(HTMLParser):
    def __init__(self, container, **kwargs):
        super().__init__(**kwargs)
        self.container = container
        self.current_layout = container
        self.layout_stack = [container]
        self.current_style = {
            'bold': False,
            'italic': False,
            'underline': False,
            'font_size': dp(14),
            'color': (0, 0, 0, 1),
            'bgcolor': None,
            'align': 'left'
        }
        self.link_url = None
        self.in_pre = False
        self.in_li = False
        self.li_count = 0
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'div':
            new_layout = BoxLayout(orientation='vertical', size_hint_y=None)
            new_layout.height = dp(30)  # 初始高度，会自动调整
            self.current_layout.add_widget(new_layout)
            self.layout_stack.append(new_layout)
            self.current_layout = new_layout

        elif tag == 'p':
            new_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30))
            self.current_layout.add_widget(new_layout)
            self.layout_stack.append(new_layout)
            self.current_layout = new_layout

        elif tag == 'h1':
            self.current_style['font_size'] = dp(28)
            self.current_style['bold'] = True

        elif tag == 'h2':
            self.current_style['font_size'] = dp(24)
            self.current_style['bold'] = True

        elif tag == 'h3':
            self.current_style['font_size'] = dp(20)
            self.current_style['bold'] = True

        elif tag == 'b' or tag == 'strong':
            self.current_style['bold'] = True

        elif tag == 'i' or tag == 'em':
            self.current_style['italic'] = True

        elif tag == 'u':
            self.current_style['underline'] = True

        elif tag == 'a':
            self.link_url = attrs_dict.get('href', '#')
            self.current_style['color'] = get_color_from_hex('#0000FF')
            self.current_style['underline'] = True

        elif tag == 'img':
            src = attrs_dict.get('src', '')
            if src:
                # 创建图片容器
                img_container = BoxLayout(orientation='vertical', size_hint_y=None)
                img_container.height = dp(200)

                # 添加图片
                img = AsyncImage(source=src, size_hint_y=None, height=dp(180))
                img_container.add_widget(img)

                # 添加图片描述（如果有）
                alt_text = attrs_dict.get('alt', '')
                if alt_text:
                    img_desc = Label(text=alt_text, size_hint_y=None, height=dp(20),
                                     font_size=dp(12), color=(0.5, 0.5, 0.5, 1))
                    img_container.add_widget(img_desc)

                self.current_layout.add_widget(img_container)

        elif tag == 'ul' or tag == 'ol':
            new_layout = BoxLayout(orientation='vertical', size_hint_y=None)
            self.current_layout.add_widget(new_layout)
            self.layout_stack.append(new_layout)
            self.current_layout = new_layout
            self.li_count = 0

        elif tag == 'li':
            self.in_li = True
            self.li_count += 1
            prefix = "• " if self.lasttag in ('ul', 'ol') else f"{self.li_count}. "
            self.current_text += prefix

        elif tag == 'br':
            self._flush_text()
            self.current_layout.add_widget(Label(text="", size_hint_y=None, height=dp(10)))

        elif tag == 'hr':
            self._flush_text()
            separator = BoxLayout(size_hint_y=None, height=dp(2))
            with separator.canvas.before:
                Color(0.7, 0.7, 0.7, 1)
                Rectangle(pos=separator.pos, size=separator.size)
            self.current_layout.add_widget(separator)

        elif tag == 'pre':
            self.in_pre = True
            self.current_style['font_size'] = dp(12)
            self.current_style['color'] = (0.2, 0.2, 0.2, 1)

        elif tag == 'code':
            self.current_style['font_size'] = dp(12)
            self.current_style['color'] = (0.2, 0.2, 0.2, 1)
            self.current_style['bgcolor'] = (0.95, 0.95, 0.95, 1)

        elif tag == 'blockquote':
            self._flush_text()
            quote_layout = BoxLayout(orientation='vertical', size_hint_y=None)
            quote_layout.height = dp(30)
            with quote_layout.canvas.before:
                Color(0.9, 0.9, 0.9, 1)
                Rectangle(pos=quote_layout.pos, size=quote_layout.size)
            self.current_layout.add_widget(quote_layout)
            self.layout_stack.append(quote_layout)
            self.current_layout = quote_layout
            self.current_style['color'] = (0.4, 0.4, 0.4, 1)

    def handle_endtag(self, tag):
        if tag in ('div', 'p', 'ul', 'ol', 'blockquote'):
            self._flush_text()
            if len(self.layout_stack) > 1:
                self.layout_stack.pop()
                self.current_layout = self.layout_stack[-1]

        elif tag in ('h1', 'h2', 'h3'):
            self._flush_text()
            self.current_style['font_size'] = dp(14)
            self.current_style['bold'] = False

        elif tag in ('b', 'strong'):
            self.current_style['bold'] = False

        elif tag in ('i', 'em'):
            self.current_style['italic'] = False

        elif tag in ('u'):
            self.current_style['underline'] = False

        elif tag == 'a':
            self._flush_text()
            self.link_url = None
            self.current_style['color'] = (0, 0, 0, 1)
            self.current_style['underline'] = False

        elif tag == 'li':
            self._flush_text()
            self.in_li = False

        elif tag == 'pre':
            self._flush_text()
            self.in_pre = False
            self.current_style['font_size'] = dp(14)
            self.current_style['color'] = (0, 0, 0, 1)

        elif tag == 'code':
            self._flush_text()
            self.current_style['font_size'] = dp(14)
            self.current_style['color'] = (0, 0, 0, 1)
            self.current_style['bgcolor'] = None

    def handle_data(self, data):
        if self.in_pre:
            # 保留预格式化文本中的空格和换行
            data = data.replace('\n', ' ')
        else:
            # 简化处理：将多个空格合并为一个
            data = re.sub(r'\s+', ' ', data).strip()

        if data:
            self.current_text += data

    def _flush_text(self):
        if self.current_text:
            # 创建自定义标签以支持基本样式
            text_label = StyledLabel(
                text=self.current_text,
                bold=self.current_style['bold'],
                italic=self.current_style['italic'],
                underline=self.current_style['underline'],
                font_size=self.current_style['font_size'],
                color=self.current_style['color'],
                bgcolor=self.current_style['bgcolor'],
                size_hint_y=None,
                height=self.current_style['font_size'] * 1.5,
                halign=self.current_style['align']
            )

            if self.link_url:
                text_label.url = self.link_url
                text_label.bind(on_touch_down=self._handle_link_click)

            self.current_layout.add_widget(text_label)
            self.current_text = ""

    def _handle_link_click(self, instance, touch):
        if instance.collide_point(*touch.pos):
            print(f"Link clicked: {instance.url}")
            # 在实际应用中，这里可以打开浏览器或处理链接
            return True
        return False


# 支持基本样式的自定义标签
class StyledLabel(Label):
    def __init__(self, bold=False, italic=False, underline=False, bgcolor=None, **kwargs):
        super().__init__(**kwargs)
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.bgcolor = bgcolor
        self.url = None

        with self.canvas.before:
            if self.bgcolor:
                Color(*self.bgcolor)
                self.rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        if hasattr(self, 'rect'):
            self.rect.pos = self.pos
            self.rect.size = self.size

    def on_texture_size(self, instance, size):
        # 根据内容自动调整高度
        self.height = max(self.font_size * 1.5, size[1])


# 网络客户端类
class NetworkClient:
    def __init__(self):
        self.tcp_socket = None
        self.tcp_thread = None
        self.tcp_running = False
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

    def tcp_connect(self, host, port):
        """建立TCP连接"""
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((host, port))
            self.tcp_running = True

            # 启动接收线程
            self.tcp_thread = threading.Thread(target=self.tcp_receive)
            self.tcp_thread.daemon = True
            self.tcp_thread.start()
            return "TCP Connected!"
        except Exception as e:
            return f"TCP Error: {str(e)}"

    def tcp_send(self, message):
        """通过TCP发送消息"""
        if self.tcp_socket:
            try:
                self.tcp_socket.send(message.encode())
                return "Message sent"
            except Exception as e:
                return f"Send Error: {str(e)}"
        return "Not connected"

    def tcp_receive(self):
        """持续接收TCP消息"""
        while self.tcp_running and self.tcp_socket:
            try:
                data = self.tcp_socket.recv(1024)
                if not data:
                    break
                if self.callback:
                    Clock.schedule_once(lambda dt: self.callback(f"TCP Received: {data.decode()}"))
            except Exception as e:
                if self.callback:
                    Clock.schedule_once(lambda dt: self.callback(f"Receive Error: {str(e)}"))
                break

    def tcp_disconnect(self):
        """断开TCP连接"""
        self.tcp_running = False
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
            self.tcp_socket = None
        return "TCP Disconnected"


# 主应用界面
class NetworkApp(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.network_client = NetworkClient()
        self.network_client.set_callback(self.update_log)

        # 创建HTTP选项卡
        http_tab = TabbedPanelItem(text='HTTP')
        http_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.http_url = TextInput(text='https://example.com', size_hint_y=None, height=40)
        self.http_data = TextInput(text='Sample data', size_hint_y=None, height=40)

        # 创建渲染容器
        self.render_container = BoxLayout(orientation='vertical', size_hint_y=0.7)
        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(self.render_container)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_get = Button(text='GET', on_press=self.send_http_get)
        btn_post = Button(text='POST', on_press=self.send_http_post)
        btn_render = Button(text='Render HTML', on_press=self.render_html)
        btn_layout.add_widget(btn_get)
        btn_layout.add_widget(btn_post)
        btn_layout.add_widget(btn_render)

        http_layout.add_widget(Label(text='URL:', size_hint_y=None, height=30))
        http_layout.add_widget(self.http_url)
        http_layout.add_widget(Label(text='Data (for POST):', size_hint_y=None, height=30))
        http_layout.add_widget(self.http_data)
        http_layout.add_widget(btn_layout)
        http_layout.add_widget(Label(text='Rendered Content:', size_hint_y=None, height=30))
        http_layout.add_widget(scroll_view)

        http_tab.add_widget(http_layout)
        self.add_widget(http_tab)

        # 创建TCP选项卡
        tcp_tab = TabbedPanelItem(text='TCP')
        tcp_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.tcp_host = TextInput(text='127.0.0.1', size_hint_y=None, height=40)
        self.tcp_port = TextInput(text='8888', size_hint_y=None, height=40)
        self.tcp_message = TextInput(text='Hello TCP!', size_hint_y=None, height=40)
        self.tcp_log = TextInput(readonly=True, size_hint_y=0.7)

        tcp_btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_connect = Button(text='Connect', on_press=self.tcp_connect)
        btn_send = Button(text='Send', on_press=self.send_tcp)
        btn_disconnect = Button(text='Disconnect', on_press=self.tcp_disconnect)
        tcp_btn_layout.add_widget(btn_connect)
        tcp_btn_layout.add_widget(btn_send)
        tcp_btn_layout.add_widget(btn_disconnect)

        tcp_layout.add_widget(Label(text='Host:', size_hint_y=None, height=30))
        tcp_layout.add_widget(self.tcp_host)
        tcp_layout.add_widget(Label(text='Port:', size_hint_y=None, height=30))
        tcp_layout.add_widget(self.tcp_port)
        tcp_layout.add_widget(Label(text='Message:', size_hint_y=None, height=30))
        tcp_layout.add_widget(self.tcp_message)
        tcp_layout.add_widget(tcp_btn_layout)
        tcp_layout.add_widget(Label(text='Log:', size_hint_y=None, height=30))
        tcp_layout.add_widget(self.tcp_log)

        tcp_tab.add_widget(tcp_layout)
        self.add_widget(tcp_tab)

        # 存储原始 HTML 内容
        self.raw_html = ""

    def update_log(self, message):
        """更新日志显示"""
        if self.current_tab.text == 'HTTP':
            # 对于HTTP，我们存储原始HTML但不直接显示在日志中
            self.raw_html = message
        else:
            self.tcp_log.text += f"{message}\n"

    def send_http_get(self, instance):
        """发送HTTP GET请求"""
        url = self.http_url.text
        result = self.network_client.http_get(url)
        self.update_log(result)
        self.render_html(None)

    def send_http_post(self, instance):
        """发送HTTP POST请求"""
        url = self.http_url.text
        data = self.http_data.text
        result = self.network_client.http_post(url, data)
        self.update_log(result)
        self.render_html(None)

    def render_html(self, instance):
        """渲染HTML内容"""
        # 清除之前的渲染内容
        self.render_container.clear_widgets()

        if not self.raw_html:
            return

        try:
            # 使用BeautifulSoup清理HTML
            soup = BeautifulSoup(self.raw_html, 'html.parser')

            # 提取主要内容（如果有）
            main_content = soup.find('main') or soup.find('article') or soup.body

            # 创建HTML渲染器
            renderer = HTMLRenderer(self.render_container)

            # 渲染清理后的HTML
            renderer.feed(str(main_content))
            renderer.close()

        except Exception as e:
            error_label = Label(text=f"渲染错误: {str(e)}", color=(1, 0, 0, 1))
            self.render_container.add_widget(error_label)

    def tcp_connect(self, instance):
        """建立TCP连接"""
        host = self.tcp_host.text
        port = int(self.tcp_port.text)
        result = self.network_client.tcp_connect(host, port)
        self.tcp_log.text += f"{result}\n"

    def send_tcp(self, instance):
        """发送TCP消息"""
        message = self.tcp_message.text
        result = self.network_client.tcp_send(message)
        self.tcp_log.text += f"{result}\n"

    def tcp_disconnect(self, instance):
        """断开TCP连接"""
        result = self.network_client.tcp_disconnect()
        self.tcp_log.text += f"{result}\n"


class NetworkDemoApp(App):
    def build(self):
        Window.size = (800, 600)
        return NetworkApp()


if __name__ == '__main__':
    NetworkDemoApp().run()