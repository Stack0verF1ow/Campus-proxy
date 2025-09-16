from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
name = "setting"

class View(Screen):
    def __init__(self):
        super().__init__()

        self.name = name
        self.add_widget(Label(text = "设置", valign= "middle"))