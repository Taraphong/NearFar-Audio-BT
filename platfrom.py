from kivy.utils import platform

class Platform:
    @staticmethod
    def is_android():
        return platform == "android"

