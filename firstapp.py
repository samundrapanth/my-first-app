from kivy.app import App
from kivy.uix.label import Label

class BasicApp(App):
    def build(self):
        label= Label(text="Hello World")
        return label
    print("before run")
BasicApp().run()

print("after run")