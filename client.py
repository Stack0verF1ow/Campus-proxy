import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
import threading
import re

# 代理配置（替换为您的ngrok地址）
PROXY_URL = 'https://9d9c90ba7a68.ngrok-free.app'


class ProxyApp(App):
    def build(self):
        # 设置窗口大小（适合移动端）
        Window.size = (360, 640)

        # 创建主布局
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        # 添加标题
        self.title_label = Label(
            text="校园代理客户端",
            font_size=dp(24),
            size_hint_y=0.1,
            color=(0, 0, 0, 1)  # 确保黑色文本
        )
        self.layout.add_widget(self.title_label)

        # 添加URL输入框
        self.url_input = TextInput(
            text='http://phoenix.stu.edu.cn/bt/default.aspx',
            multiline=False,
            size_hint_y=0.1,
            font_size=dp(16),
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1)
        )
        self.layout.add_widget(self.url_input)

        # 添加进度条
        self.progress = ProgressBar(max=100, size_hint_y=0.05)
        self.layout.add_widget(self.progress)
        self.progress.value = 0

        # 创建滚动视图用于显示结果
        scroll_view = ScrollView(size_hint_y=0.6)
        self.result_label = Label(
            text="点击下方按钮开始测试代理...",
            text_size=(Window.width - dp(20), None),
            halign='left',
            valign='top',
            padding=(dp(10), dp(10)),
            markup=True,
            color=(0, 0, 0, 1),
            font_size=dp(16)
        )
        scroll_view.add_widget(self.result_label)
        self.layout.add_widget(scroll_view)

        # 添加按钮
        self.test_button = Button(
            text="测试代理连接",
            size_hint_y=0.1,
            font_size=dp(18),
            background_color=(0.2, 0.6, 1, 1),
            on_press=self.start_test
        )
        self.layout.add_widget(self.test_button)

        return self.layout

    def start_test(self, instance):
        """开始测试代理连接"""
        self.test_button.disabled = True
        self.test_button.text = "连接中..."
        self.progress.value = 30
        self.result_label.text = "[b]正在连接代理服务器...[/b]"

        # 在新线程中执行网络请求
        threading.Thread(target=self.get_data).start()

    def get_data(self):
        """从代理服务器获取数据"""
        try:
            url = self.url_input.text.strip()
            if not url:
                url = 'http://phoenix.stu.edu.cn/bt/default.aspx'

            # 更新UI显示当前操作
            Clock.schedule_once(lambda dt: setattr(
                self.result_label, 'text',
                f"[b]正在通过代理访问:[/b]\n{url}"
            ), 0)

            response = requests.get(
                url,
                proxies={'https': PROXY_URL},
                timeout=15
            )

            # 更新进度条
            Clock.schedule_once(lambda dt: setattr(self.progress, 'value', 70), 0)

            # 处理响应
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')

                # 尝试检测编码
                encoding = response.encoding
                if 'charset=' in content_type:
                    charset_match = re.search(r'charset=([\w-]+)', content_type)
                    if charset_match:
                        encoding = charset_match.group(1)

                # 使用检测到的编码解码内容
                try:
                    decoded_content = response.content.decode(encoding)
                except:
                    # 如果解码失败，尝试常见编码
                    for enc in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                        try:
                            decoded_content = response.content.decode(enc)
                            break
                        except:
                            continue
                    else:
                        decoded_content = response.text  # 最后尝试使用requests的自动解码

                if 'application/json' in content_type:
                    result = self.parse_json(decoded_content)
                elif 'text/html' in content_type:
                    result = self.parse_html(decoded_content)
                else:
                    result = f"[b]成功接收数据[/b]\n类型: {content_type}\n大小: {len(response.content)}字节"
            else:
                result = f"[b]错误状态码: {response.status_code}[/b]\n响应内容: {response.text[:200]}"

            # 在主线程更新UI
            Clock.schedule_once(lambda dt: self.update_result(result), 0)

        except Exception as e:
            import traceback
            error_msg = f"[color=ff0000][b]请求失败:[/b] {str(e)}[/color]\n\n{traceback.format_exc()}"
            Clock.schedule_once(lambda dt: self.update_result(error_msg), 0)

        finally:
            # 重置按钮状态
            Clock.schedule_once(lambda dt: setattr(self.test_button, 'disabled', False), 0)
            Clock.schedule_once(lambda dt: setattr(self.test_button, 'text', "测试代理连接"), 0)
            Clock.schedule_once(lambda dt: setattr(self.progress, 'value', 100), 0)

    def parse_json(self, data):
        """解析JSON数据"""
        try:
            import json
            json_data = json.loads(data)

            # 简单展示JSON结构
            if isinstance(json_data, dict):
                keys = list(json_data.keys())
                result = "[b]JSON数据包含以下键:[/b]\n" + ", ".join(keys)

                # 添加前几个键值对
                sample = "\n\n[b]数据示例:[/b]"
                for i, key in enumerate(keys[:3]):
                    value = str(json_data[key])[:100] + "..." if len(str(json_data[key])) > 100 else str(json_data[key])
                    sample += f"\n{key}: {value}"

                return result + sample
            return f"[b]JSON数据:[/b]\n{str(json_data)[:500]}..."
        except Exception as e:
            return f"[color=ff0000][b]JSON解析错误:[/b] {str(e)}[/color]\n原始数据:\n{data[:500]}"

    def parse_html(self, html):
        """解析HTML内容"""
        try:
            # 尝试提取标题
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "未找到标题"

            # 清理HTML标签
            clean_text = re.sub(r'<[^>]+>', ' ', html)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            # 截取前300个字符
            preview = clean_text[:300] + "..." if len(clean_text) > 300 else clean_text

            return f"[b]页面标题:[/b] {title}\n\n[b]内容预览:[/b]\n{preview}"
        except Exception as e:
            return f"[color=ff0000][b]HTML解析错误:[/b] {str(e)}[/color]\n原始数据:\n{html[:500]}"

    def update_result(self, text):
        """更新结果显示"""
        self.result_label.text = text
        self.progress.value = 100


if __name__ == '__main__':
    ProxyApp().run()