from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
import threading


class FixedSeleniumApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10)

        self.status_label = Label(text="准备访问网站...")
        self.content_label = Label(text="", size_hint_y=0.8)

        btn = Button(text="访问 phoenix.stu.edu.cn", size_hint_y=0.1)
        btn.bind(on_press=self.fetch_website)

        layout.add_widget(self.status_label)
        layout.add_widget(self.content_label)
        layout.add_widget(btn)

        return layout

    def fetch_website(self, instance):
        self.status_label.text = "正在加载网页..."
        threading.Thread(target=self._fetch_website_thread).start()

    def _fetch_website_thread(self):
        try:
            # 使用 WebDriver Manager 自动管理驱动
            service = Service(ChromeDriverManager().install())

            # 配置 Chrome 选项
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # 初始化浏览器
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # 设置页面加载超时
            driver.set_page_load_timeout(30)

            # 访问目标网站
            driver.get("http://phoenix.stu.edu.cn/Nav/")

            # 使用显式等待确保页面加载完成
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # 额外等待确保内容加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 获取页面内容
            page_source = driver.page_source

            # 更新 UI
            Clock.schedule_once(lambda dt: self.update_ui(page_source))
        except Exception as e:
            # 使用默认参数捕获当前值
            Clock.schedule_once(lambda dt, error=str(e): self.update_error(error))
        finally:
            if 'driver' in locals():
                driver.quit()

    def update_ui(self, content):
        self.status_label.text = "网页加载完成"
        # 检查内容是否为空
        if len(content.strip()) < 100:
            self.content_label.text = "警告: 获取到的内容可能不完整\n\n" + content
        else:
            self.content_label.text = f"获取内容长度: {len(content)} 字符\n\n前500字符:\n{content[:500]}..."

    def update_error(self, error):
        self.status_label.text = "加载失败"
        self.content_label.text = f"错误信息:\n{error}"


if __name__ == '__main__':
    FixedSeleniumApp().run()