from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
name = "forums"

class View(Screen):
    def __init__(self):
        super().__init__()

        self.name = name
        self.add_widget(Label(text = "论坛", valign= "middle"))