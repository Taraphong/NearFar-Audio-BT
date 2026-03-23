from kivy.clock import Clock
from kivy.utils import platform
from time import monotonic

IS_ANDROID = platform == "android"

if IS_ANDROID:
    from android.broadcast import BroadcastReceiver  # type: ignore
    from android.permissions import Permission, request_permissions  # type: ignore
    from jnius import PythonJavaClass, autoclass, java_method

    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")


if IS_ANDROID:
    class BLEScanCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]
        __javacontext__ = "app"

        def __init__(self, scanner):
            super().__init__()
            self.scanner = scanner

        @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
        def onLeScan(self, device, rssi, _scan_record):
            self.scanner._emit_device(device, int(rssi), "ble")


class BluetoothScanner:
    def __init__(self, on_device_found, on_status, on_log):
        self.on_device_found = on_device_found
        self.on_status = on_status
        self.on_log = on_log
        self.adapter = None
        self.receiver = None
        self.scanning = False
        self.ble_callback = None
        self.selected_address = None
        self.track_selected_mode = False
        self._last_emit = {}

    def request_permissions(self):
        if not IS_ANDROID:
            return
        perms = [
            Permission.BLUETOOTH,
            Permission.BLUETOOTH_ADMIN,
            Permission.ACCESS_FINE_LOCATION,
            Permission.ACCESS_COARSE_LOCATION,
            "android.permission.ACCESS_BACKGROUND_LOCATION",
            "android.permission.BLUETOOTH_SCAN",
            "android.permission.BLUETOOTH_CONNECT",
            "android.permission.MODIFY_AUDIO_SETTINGS",
            "android.permission.POST_NOTIFICATIONS",
        ]
        request_permissions(perms)

    def initialize(self):
        if not IS_ANDROID:
            return False
        self.adapter = BluetoothAdapter.getDefaultAdapter()
        return self.adapter is not None

    def _ensure_receiver(self):
        if not IS_ANDROID or self.receiver is not None:
            return
        self.receiver = BroadcastReceiver(
            self._on_bluetooth_event,
            actions=[
                BluetoothDevice.ACTION_FOUND,
                BluetoothAdapter.ACTION_DISCOVERY_STARTED,
                BluetoothAdapter.ACTION_DISCOVERY_FINISHED,
            ],
        )
        self.receiver.start()

    def _emit_device(self, device, rssi, source):
        if device is None:
            return
        address = device.getAddress() or "N/A"
        if self.track_selected_mode and self.selected_address and address != self.selected_address:
            return
        now = monotonic()
        prev = self._last_emit.get(address)
        if prev is not None:
            prev_rssi, prev_t = prev
            if (
                isinstance(rssi, int)
                and isinstance(prev_rssi, int)
                and abs(rssi - prev_rssi) < 2
                and (now - prev_t) < 1.5
            ):
                return
            if rssi is None and (now - prev_t) < 3.0:
                return
        self._last_emit[address] = (rssi, now)
        name = device.getName() or "Unknown"
        Clock.schedule_once(
            lambda *_: self.on_device_found(
                address=address,
                name=name,
                rssi=rssi,
                source=source,
            ),
            0,
        )

    def _load_paired_devices(self):
        if not IS_ANDROID or self.adapter is None:
            return
        try:
            bonded = self.adapter.getBondedDevices()
            if bonded is None:
                return
            iterator = bonded.iterator()
            while iterator.hasNext():
                device = iterator.next()
                self._emit_device(device, None, "paired")
        except Exception as exc:
            self.on_log(f"Load paired error: {exc}")

    def _on_bluetooth_event(self, _context, intent):
        action = intent.getAction()
        if action == BluetoothAdapter.ACTION_DISCOVERY_STARTED:
            Clock.schedule_once(lambda *_: self.on_status("Scanning Bluetooth..."), 0)
            return
        if action == BluetoothAdapter.ACTION_DISCOVERY_FINISHED:
            if self.scanning:
                Clock.schedule_once(lambda *_: self._restart_discovery(), 0.5)
            return
        if action == BluetoothDevice.ACTION_FOUND:
            device = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
            if device is None:
                return
            rssi = int(intent.getShortExtra(BluetoothDevice.EXTRA_RSSI, -999))
            self._emit_device(device, rssi, "classic")

    def _restart_discovery(self):
        if not IS_ANDROID or not self.scanning or self.adapter is None:
            return
        try:
            if self.adapter.isDiscovering():
                self.adapter.cancelDiscovery()
            self.adapter.startDiscovery()
        except Exception as exc:
            self.on_log(f"Discovery restart error: {exc}")

    def start_scan(self):
        if not IS_ANDROID:
            self.on_status("Android only")
            return
        if self.adapter is None:
            self.on_status("No Bluetooth adapter")
            return
        if not self.adapter.isEnabled():
            self.on_status("Bluetooth is OFF")
            return
        self._ensure_receiver()
        self.scanning = True
        self.track_selected_mode = False
        self._load_paired_devices()
        try:
            if self.adapter.isDiscovering():
                self.adapter.cancelDiscovery()
            started = bool(self.adapter.startDiscovery())
            self.on_status("Scan started" if started else "Scan start failed")
        except Exception as exc:
            self.on_status(f"Scan error: {exc}")

        if self.ble_callback is None:
            self.ble_callback = BLEScanCallback(self)
        try:
            ble_started = bool(self.adapter.startLeScan(self.ble_callback))
            self.on_log(f"BLE scan started={ble_started}")
        except Exception as exc:
            self.on_log(f"BLE start error: {exc}")

    def set_selected_device(self, address):
        self.selected_address = address
        if self.track_selected_mode:
            self._ensure_ble_tracking()

    def stop_scan(self):
        if IS_ANDROID and self.adapter is not None:
            try:
                if self.adapter.isDiscovering():
                    self.adapter.cancelDiscovery()
            except Exception as exc:
                self.on_log(f"Stop scan error: {exc}")
        # Keep BLE scan alive for selected device tracking after pressing Stop.
        if self.selected_address:
            self.track_selected_mode = True
            self._ensure_ble_tracking()
            self.scanning = False
            self.on_status("Full scan stopped, tracking selected device")
            return

        if IS_ANDROID and self.adapter is not None:
            self._stop_ble()
            self.track_selected_mode = False
        self.scanning = False
        self.on_status("Scan stopped")

    def _ensure_ble_tracking(self):
        if not IS_ANDROID or self.adapter is None:
            return
        if self.ble_callback is None:
            self.ble_callback = BLEScanCallback(self)
        try:
            self.adapter.stopLeScan(self.ble_callback)
        except Exception:
            pass
        try:
            started = bool(self.adapter.startLeScan(self.ble_callback))
            self.on_log(f"BLE tracking started={started} target={self.selected_address}")
        except Exception as exc:
            self.on_log(f"BLE tracking error: {exc}")

    def _stop_ble(self):
        if not IS_ANDROID or self.adapter is None or self.ble_callback is None:
            return
        try:
            self.adapter.stopLeScan(self.ble_callback)
        except Exception as exc:
            self.on_log(f"Stop BLE error: {exc}")

    def shutdown(self):
        self.track_selected_mode = False
        if IS_ANDROID and self.adapter is not None:
            self._stop_ble()
            try:
                if self.adapter.isDiscovering():
                    self.adapter.cancelDiscovery()
            except Exception as exc:
                self.on_log(f"Shutdown discovery stop error: {exc}")
        self.scanning = False
        self.on_status("Scan stopped")
        if self.receiver is not None:
            self.receiver.stop()
            self.receiver = None
