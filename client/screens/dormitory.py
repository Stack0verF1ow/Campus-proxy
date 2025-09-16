from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
name = "dormitory"

class View(Screen):
    def __init__(self):
        super().__init__()

        self.name = name
        self.add_widget(Label(text = "寝室", valign= "middle"))