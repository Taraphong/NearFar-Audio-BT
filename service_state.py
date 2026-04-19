import json
import os

from app_platform import App_Platform

IS_ANDROID = App_Platform.is_android()

if IS_ANDROID:
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")


class ServiceStateStore:
    def __init__(self, on_log):
        self.on_log = on_log
        self.path = None

    def initialize(self):
        if not IS_ANDROID:
            return
        try:
            activity = PythonActivity.mActivity
            files_dir = activity.getFilesDir().getAbsolutePath()
            self.path = os.path.join(files_dir, "blerssi_state.json")
            self.on_log(f"Service state path: {self.path}")
        except Exception as exc:
            self.on_log(f"Service state init error: {exc}")

    def write(self, selected_address, rssi_threshold):
        if not self.path:
            return
        payload = {
            "selected_address": selected_address,
            "rssi_threshold": int(rssi_threshold),
        }
        try:
            with open(self.path, "w", encoding="utf-8") as file_obj:
                json.dump(payload, file_obj)
        except Exception as exc:
            self.on_log(f"Service state write error: {exc}")
