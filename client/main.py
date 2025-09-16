import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, NoTransition, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.utils import get_color_from_hex
from kivy.graphics import Rectangle, Color

from screens import personal, index, forums, dormitory, login, setting
from utils.db_connect import connect_db_except

script_dir = os.path.dirname(os.path.abspath(__file__))
# 构建字体文件的绝对路径
font_path = os.path.join(script_dir, "utils", "fangzhen.ttf")
# 注册字体（使用绝对路径）
LabelBase.register("main_theme", font_path)

Window.size = (412, 735)
Pages ={index.name : index.View(),
              forums.name : forums.View(),
              personal.name : personal.View(),
              dormitory.name : dormitory.View(),
              login.name : login.View()
              }

Screens = {
    login.name : login.View(),
    setting.name : setting.View(),
}


class MenuButton(Button):
    def __init__(self, text, img, click_img, name):
        super().__init__()
        self.name = name
        self.text = text
        self.color = get_color_from_hex("#666666")
        self.background_color = (1, 1, 1, 0)
        self.halign = "center"
        self.valign = "bottom"
        self.font_size = "20sp"
        self.line_height = "0.8sp"
        self.bind(pos=self.update_img, size=self.update_img)
        self.img = img
        self.click_img = click_img
        self.is_click = False
        self.register_event_type('on_button_pressed')
        with self.canvas.before:
            self.back_img = Rectangle(source=self.img)

    def on_press(self):
        self.is_click = True
        # 触发自定义事件，通知父组件按钮被按下
        self.dispatch('on_button_pressed', self.name)

    def set_img(self):
        if self.is_click:
            self.back_img.source = self.click_img
        else:
            self.back_img.source = self.img
        self.is_click = False

    def update_img(self, widget, values):
        self.back_img.size = (widget.width / 2, widget.width / 2)
        self.back_img.pos = (widget.pos[0] + (widget.width / 4), widget.height - self.back_img.size[1])
        self.text_size = widget.size

    # 定义自定义事件
    def on_button_pressed(self, screen_name):
        """自定义事件，当按钮被按下时触发"""
        pass

class Menu(BoxLayout):
    def __init__(self, screen_manager):
        super().__init__()
        self.screen_manager = screen_manager
        self.size_hint = (1, 0.1)
        with self.canvas.before:
            Color(1, 1, 1)
            self.back = Rectangle()

        # 创建按钮并绑定事件
        buttons = [
            ("首页", "./static/master_i.png", "./static/master_o.png", "index"),
            ("校园论坛", "./static/socket_i.png", "./static/socket_o.png", "forums"),
            ("寝室", "./static/message_i.png", "./static/message_o.png", "dormitory"),
            ("个人", "./static/personal_i.png", "./static/personal_o.png", "personal")
        ]

        for text, img, click_img, name in buttons:
            button = MenuButton(text=text, img=img, click_img=click_img, name=name)
            # 绑定按钮的自定义事件到处理方法
            button.bind(on_button_pressed=self.handle_button_pressed)
            self.add_widget(button)

        self.bind(size=self.update_back)

    def handle_button_pressed(self, button_instance, screen_name):
        """处理按钮按下事件，切换屏幕并更新按钮状态"""
        # 更新所有按钮状态
        self.on_press_update()

        # 切换屏幕
        if self.screen_manager:
            self.screen_manager.current = screen_name

    def on_press_update(self):
        for child in self.children:
            if isinstance(child, MenuButton):
                child.set_img()

    def update_back(self, widget, size):
        self.back.size = size

class MainApp(App):
    def build(self):

        main_screen = Screen(name= "main")

        pages = ScreenManager(size_hint = (1, 0.92), pos_hint = {"x": 0, "top": 1}, transition= NoTransition())
        for page in Pages.values():
            pages.add_widget(page)

        #主屏幕由多个页面组成，由菜单切换
        main_screen.add_widget(pages)
        main_screen.add_widget(Menu(screen_manager= pages))

        self.client = client = ScreenManager(transition= NoTransition())
        client.add_widget(main_screen)
        for screen in Screens.values():
            client.add_widget(screen)

        return client

    def on_start(self):
       if connect_db_except("select * from Cookies where id= 0") == [] :
            self.client.current = login.name

MainApp().run()