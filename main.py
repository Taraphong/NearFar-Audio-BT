from datetime import datetime
import json
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from output import AudioOutputController
from pullrssi import RSSIRepository
from scan import IS_ANDROID, BluetoothScanner

if IS_ANDROID:
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Context = autoclass("android.content.Context")
    PowerManager = autoclass("android.os.PowerManager")
    Uri = autoclass("android.net.Uri")
    ServiceBg = autoclass("org.example.blerssi.ServiceBg")


class BluetoothAudioApp(App):
    RSSI_THRESHOLD = -60

    def build(self):
        self.repo = RSSIRepository()
        self.log_lines = []
        self.bg_wakelock = None
        self.service_state_path = None
        self._refresh_trigger = Clock.create_trigger(self._refresh_spinner_values, 0.25)
        self.scanner = BluetoothScanner(
            on_device_found=self.on_device_found,
            on_status=self.on_scan_status,
            on_log=self.write_log,
        )
        self.output = AudioOutputController(on_log=self.write_log)

        root = BoxLayout(orientation="vertical", padding=8, spacing=8)

        nav = BoxLayout(size_hint_y=None, height="44dp", spacing=8)
        self.scan_page_btn = Button(text="Scan")
        self.log_page_btn = Button(text="Log")
        nav.add_widget(self.scan_page_btn)
        nav.add_widget(self.log_page_btn)
        root.add_widget(nav)

        self.manager = ScreenManager(transition=NoTransition())

        scan_screen = Screen(name="scan")
        scan_layout = BoxLayout(orientation="vertical", padding=8, spacing=8)

        self.status_label = Label(
            text="Initializing...",
            size_hint_y=None,
            height="44dp",
            bold=True,
            halign="left",
            valign="middle",
        )
        self.status_label.bind(size=self._resize_status)
        scan_layout.add_widget(self.status_label)

        self.rssi_label = Label(
            text="Selected RSSI: N/A",
            size_hint_y=None,
            height="36dp",
            halign="left",
            valign="middle",
        )
        self.rssi_label.bind(size=self._resize_rssi)
        scan_layout.add_widget(self.rssi_label)

        self.device_spinner = Spinner(
            text="Select smart watch device",
            values=(),
            size_hint_y=None,
            height="44dp",
        )
        self.device_spinner.bind(text=self._on_select_device)
        scan_layout.add_widget(self.device_spinner)

        button_row = BoxLayout(size_hint_y=None, height="44dp", spacing=8)
        self.scan_btn = Button(text="Start Scan")
        self.stop_btn = Button(text="Stop Scan")
        button_row.add_widget(self.scan_btn)
        button_row.add_widget(self.stop_btn)
        scan_layout.add_widget(button_row)

        scan_scroll = ScrollView(size_hint_y=1)
        self.scan_list_label = Label(
            text="No device scanned yet",
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        self.scan_list_label.bind(texture_size=self.scan_list_label.setter("size"))
        scan_scroll.add_widget(self.scan_list_label)
        scan_layout.add_widget(scan_scroll)

        scan_screen.add_widget(scan_layout)
        self.manager.add_widget(scan_screen)

        log_screen = Screen(name="log")
        log_layout = BoxLayout(orientation="vertical", padding=8, spacing=8)
        clear_log_btn = Button(text="Clear Log", size_hint_y=None, height="44dp")
        clear_log_btn.bind(on_release=lambda *_: self.clear_logs())
        log_layout.add_widget(clear_log_btn)

        scroll = ScrollView(size_hint_y=1)
        self.log_label = Label(
            text="System Log:\n",
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        self.log_label.bind(texture_size=self.log_label.setter("size"))
        scroll.add_widget(self.log_label)
        log_layout.add_widget(scroll)
        log_screen.add_widget(log_layout)
        self.manager.add_widget(log_screen)

        root.add_widget(self.manager)

        self.scan_page_btn.bind(on_release=lambda *_: self.show_scan())
        self.log_page_btn.bind(on_release=lambda *_: self.show_log())
        self.scan_btn.bind(on_release=lambda *_: self.scanner.start_scan())
        self.stop_btn.bind(on_release=lambda *_: self.scanner.stop_scan())

        if IS_ANDROID:
            self.scanner.request_permissions()
            if not self.scanner.initialize():
                self.on_scan_status("No Bluetooth adapter")
            self.output.initialize()
            self._init_service_state_file()
            self._request_ignore_battery_optimizations()
            self._start_foreground_service()
        else:
            self.on_scan_status("Android only")

        Clock.schedule_interval(self.apply_selected_device_output, 0.8)
        self.scanner.start_scan()
        return root

    def show_scan(self):
        self.manager.current = "scan"

    def show_log(self):
        self.manager.current = "log"

    def _resize_status(self, *_):
        self.status_label.text_size = (self.status_label.width, None)

    def _resize_rssi(self, *_):
        self.rssi_label.text_size = (self.rssi_label.width, None)

    def clear_logs(self):
        self.log_lines = []
        self.log_label.text = "System Log:\n"

    def write_log(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_lines.append(f"[{timestamp}] {text}")
        # Keep log compact to avoid UI slowdown.
        if len(self.log_lines) > 120:
            self.log_lines = self.log_lines[-120:]
        self.log_label.text = "System Log:\n" + "\n".join(self.log_lines)

    def on_scan_status(self, text):
        if text in {"Scan started", "Scanning Bluetooth..."}:
            # Clear logs at each new scan round.
            self.clear_logs()
        if text in {"play on speaker", "play on Bluetooth"}:
            self.status_label.text = text
        elif self.status_label.text not in {"play on speaker", "play on Bluetooth"}:
            self.status_label.text = text
        self.write_log(text)

    def on_device_found(self, address, name, rssi, source="unknown"):
        device = self.repo.update_device(address, name, rssi, source)
        if source == "paired":
            self._refresh_trigger()
            return
        rssi_text = f"{device['rssi']} dBm" if isinstance(device["rssi"], int) else "N/A"
        self.write_log(f"Found {name} ({address}) RSSI={rssi_text} source={source}")
        self._refresh_trigger()

    def _refresh_spinner_values(self, *_):
        self.device_spinner.values = self.repo.spinner_values()
        self.scan_list_label.text = self.repo.scan_list_text()
        if self.repo.selected_address is not None:
            selected = self.repo.get_device(self.repo.selected_address)
            if selected is not None:
                rssi_text = (
                    f"{selected['rssi']} dBm"
                    if isinstance(selected["rssi"], int)
                    else "N/A"
                )
                self.device_spinner.text = (
                    f"{selected['name']} | {self.repo.selected_address} | "
                    f"{rssi_text} | {selected.get('source', 'n/a')}"
                )

    def _on_select_device(self, _spinner, text):
        address = self.repo.select_from_spinner_text(text)
        if not address:
            return
        self.scanner.set_selected_device(address)
        self._write_service_state()
        self.write_log(f"Selected device: {text}")
        self.apply_selected_device_output(0)

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
        self._release_wakelock()
        self.scanner.shutdown()

    def on_pause(self):
        # Keep app logic running while activity is in background.
        self._acquire_wakelock()
        self.write_log("App moved to background")
        return True

    def on_resume(self):
        self._release_wakelock()
        self.write_log("App resumed from background")

    def _acquire_wakelock(self):
        if not IS_ANDROID or self.bg_wakelock is not None:
            return
        try:
            activity = PythonActivity.mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            tag = "blerssi:background"
            self.bg_wakelock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, tag)
            self.bg_wakelock.acquire()
            self.write_log("Background wakelock acquired")
        except Exception as exc:
            self.write_log(f"Wakelock acquire error: {exc}")

    def _release_wakelock(self):
        if self.bg_wakelock is None:
            return
        try:
            if self.bg_wakelock.isHeld():
                self.bg_wakelock.release()
            self.write_log("Background wakelock released")
        except Exception as exc:
            self.write_log(f"Wakelock release error: {exc}")
        finally:
            self.bg_wakelock = None

    def _request_ignore_battery_optimizations(self):
        if not IS_ANDROID:
            return
        try:
            activity = PythonActivity.mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            package_name = activity.getPackageName()
            if pm is not None and pm.isIgnoringBatteryOptimizations(package_name):
                self.write_log("Battery optimization already ignored")
                return
            intent = Intent("android.settings.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS") #type: ignore
            intent.setData(Uri.parse(f"package:{package_name}"))
            activity.startActivity(intent)
            self.write_log("Requested ignore battery optimization")
        except Exception as exc:
            self.write_log(f"Battery optimization request error: {exc}")

    def _start_foreground_service(self):
        if not IS_ANDROID:
            return
        try:
            activity = PythonActivity.mActivity
            # python-for-android service classes expose static start(context, arg)
            # and handle proper startForegroundService/startService internally.
            ServiceBg.start(activity, "")
            self.write_log("Foreground service started (ServiceBg.start)")
        except Exception as exc:
            self.write_log(f"Foreground service start error (start): {exc}")

    def _init_service_state_file(self):
        if not IS_ANDROID:
            return
        try:
            activity = PythonActivity.mActivity
            files_dir = activity.getFilesDir().getAbsolutePath()
            self.service_state_path = os.path.join(files_dir, "blerssi_state.json")
            self._write_service_state()
            self.write_log(f"Service state path: {self.service_state_path}")
        except Exception as exc:
            self.write_log(f"Service state init error: {exc}")

    def _write_service_state(self):
        if not self.service_state_path:
            return
        payload = {
            "selected_address": self.repo.selected_address,
            "rssi_threshold": int(self.RSSI_THRESHOLD),
        }
        try:
            with open(self.service_state_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            self.write_log(f"Service state write error: {exc}")


if __name__ == "__main__":
    BluetoothAudioApp().run()
