from holoviews.plotting.bokeh.styles import font_size
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button


name = "login"

class View(Screen):
    def __init__(self):
        super().__init__()
        self.name = name
        self.add_widget(Button(text= "确认登陆", on_press= self.login))

        self.user_name_box = TextInput(size_hint= (0.6, 0.1),  pos_hint= {"x": 0.25, "top": 0.5}, multiline= False, halign= "left", font_size= "24sp", line_height="1sp")
        self.pass_word_box = TextInput(size_hint= (0.6, 0.1),  pos_hint= {"x": 0.25, "top": 0.6}, multiline= False, halign= "left", font_size= "24sp", line_height="1sp" )

        self.add_widget(self.user_name_box)
        self.add_widget(self.pass_word_box)

    def login(self, widget):
        self.manager.current = "main"