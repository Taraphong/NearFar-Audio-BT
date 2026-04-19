from kivy.app import App
from kivy.clock import Clock

from output import AudioOutputController
from pullrssi import RSSIRepository
from scan import BluetoothScanner
from app_platform import App_Platform
from android_helpers import AndroidLifecycleHelper
from service_state import ServiceStateStore
from log_controller import LogController
from ui_controller import UIController
from ui import build_main_ui

IS_ANDROID = App_Platform.is_android()


class BluetoothAudioApp(App):
    RSSI_THRESHOLD = -60

    def build(self):
        self.repo = RSSIRepository()
        self.log_lines = []
        self.log_controller = LogController(self)
        self.ui_controller = UIController(self)
        self.android_lifecycle = AndroidLifecycleHelper(on_log=self.write_log)
        self.service_state = ServiceStateStore(on_log=self.write_log)
        self._refresh_trigger = Clock.create_trigger(
            self.ui_controller.refresh_spinner_values, 0.25
        )
        self.scanner = BluetoothScanner(
            on_device_found=self.on_device_found,
            on_status=self.on_scan_status,
            on_log=self.write_log,
        )
        self.output = AudioOutputController(on_log=self.write_log)
        root = build_main_ui(self)

        if IS_ANDROID:
            App_Platform.request_permissions()
            if not self.scanner.initialize():
                self.on_scan_status("No Bluetooth adapter")
            self.output.initialize()
            self.service_state.initialize()
            self._write_service_state()
            self.android_lifecycle.request_ignore_battery_optimizations()
            self.android_lifecycle.start_foreground_service()
        else:
            self.on_scan_status("Android only")

        Clock.schedule_interval(self.apply_selected_device_output, 0.8)
        self.scanner.start_scan()
        return root

    def show_scan(self):
        self.ui_controller.show_scan()

    def show_log(self):
        self.ui_controller.show_log()

    def _resize_status(self, *_):
        self.status_label.text_size = (self.status_label.width, None)

    def _resize_rssi(self, *_):
        self.rssi_label.text_size = (self.rssi_label.width, None)

    def clear_logs(self):
        self.log_controller.clear_logs()

    def write_log(self, text):
        self.log_controller.write_log(text)

    def on_scan_status(self, text):
        self.log_controller.on_scan_status(text)

    def on_device_found(self, address, name, rssi, source="unknown"):
        device = self.repo.update_device(address, name, rssi, source)
        if source == "paired":
            self._refresh_trigger()
            return
        rssi_text = f"{device['rssi']} dBm" if isinstance(device["rssi"], int) else "N/A"
        self.write_log(f"Found {name} ({address}) RSSI={rssi_text} source={source}")
        self._refresh_trigger()

    def _refresh_spinner_values(self, *_):
        self.ui_controller.refresh_spinner_values(*_)

    def _on_select_device(self, _spinner, text):
        self.ui_controller.on_select_device(_spinner, text)

    def apply_selected_device_output(self, _dt):
        if self.repo.selected_address is None:
            self.rssi_label.text = "Selected RSSI: N/A"
            return

        item = self.repo.get_device(self.repo.selected_address)
        if item is None or not isinstance(item.get("rssi"), int):
            self.rssi_label.text = "Selected RSSI: N/A"
            return

        rssi = int(item["rssi"])
        self.rssi_label.text = f"Selected RSSI: {rssi} dBm"
        state = self.output.apply_output_for_rssi(rssi, self.RSSI_THRESHOLD)
        if state is not None:
            status_text, color = state
            self.status_label.text = status_text
            self.status_label.color = color

    def on_stop(self):
        self.android_lifecycle.release_wakelock()
        self.scanner.shutdown()

    def on_pause(self):
        # Keep app logic running while activity is in background.
        self.android_lifecycle.acquire_wakelock()
        self.write_log("App moved to background")
        return True

    def on_resume(self):
        self.android_lifecycle.release_wakelock()
        self.write_log("App resumed from background")

    def _write_service_state(self):
        self.service_state.write(
            selected_address=self.repo.selected_address,
            rssi_threshold=self.RSSI_THRESHOLD,
        )


if __name__ == "__main__":
    BluetoothAudioApp().run()
