from kivy.clock import Clock
from time import monotonic
from app_platform import App_Platform

IS_ANDROID = App_Platform.is_android()

if IS_ANDROID:
    from android.broadcast import BroadcastReceiver  # type: ignore
    from jnius import PythonJavaClass, autoclass, java_method

    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")

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
        self._discovery_attempts = 0
        self._last_status = None
        self._last_log = {}

    def request_permissions(self):
        if not IS_ANDROID:
            return
        Platform.request_permissions()

    def _status(self, text):
        if text == self._last_status:
            return
        self._last_status = text
        self.on_status(text)

    def _log(self, text):
        now = monotonic()
        prev = self._last_log.get(text)
        if prev is not None and (now - prev) < 1.0:
            return
        self._last_log[text] = now
        self.on_log(text)

    def initialize(self):
        if not IS_ANDROID:
            return False
        self.adapter = BluetoothAdapter.getDefaultAdapter()
        return self.adapter is not None

    def _missing_scan_permissions(self):
        return Platform.missing_bluetooth_permissions()

    def is_gps_enabled(self):
        enabled = Platform.is_location_service_enabled()
        if not enabled:
            self._log("Location service unavailable or disabled")
        return enabled

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
            self._log(f"Load paired error: {exc}")

    def _on_bluetooth_event(self, _context, intent):
        action = intent.getAction()
        if action == BluetoothAdapter.ACTION_DISCOVERY_STARTED:
            Clock.schedule_once(lambda *_: self._status("Scanning Bluetooth..."), 0)
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
                Clock.schedule_once(lambda *_: self._restart_discovery(), 0.4)
                return
            self.adapter.startDiscovery()
        except Exception as exc:
            self._log(f"Discovery restart error: {exc}")

    def _attempt_start_discovery(self):
        if not IS_ANDROID or not self.scanning or self.adapter is None:
            return
        self._discovery_attempts += 1
        try:
            if self.adapter.isDiscovering():
                self.adapter.cancelDiscovery()
                Clock.schedule_once(lambda *_: self._attempt_start_discovery(), 0.4)
                return
            started = bool(self.adapter.startDiscovery())
            if started:
                self._status("Scan started")
                self._log(f"Classic discovery started (attempt {self._discovery_attempts})")
                return
            if self._discovery_attempts < 3:
                self._log(
                    f"Classic discovery returned False on attempt {self._discovery_attempts}, retrying..."
                )
                Clock.schedule_once(lambda *_: self._attempt_start_discovery(), 0.7)
                return
            self._status("Scan start failed")
            self._log("Classic discovery failed after 3 attempts")
        except Exception as exc:
            if self._discovery_attempts < 3:
                self._log(
                    f"Discovery attempt {self._discovery_attempts} error: {exc}; retrying..."
                )
                Clock.schedule_once(lambda *_: self._attempt_start_discovery(), 0.7)
                return
            self._status(f"Scan error: {exc}")

    def start_scan(self):
        if not IS_ANDROID:
            self._status("Android only")
            return
        if self.adapter is None:
            self._status("No Bluetooth adapter")
            return
        if not self.adapter.isEnabled():
            self._status("Bluetooth is OFF")
            return
        missing_permissions = self._missing_scan_permissions()
        if missing_permissions:
            self._status("Missing Bluetooth permissions")
            self._log(f"Missing permissions: {', '.join(missing_permissions)}")
            self.request_permissions()
            return
        if not self.is_gps_enabled():
            self._status("GPS / Location is OFF")
            self._log("Bluetooth scan requires GPS / Location service to be enabled")
            return
        self._ensure_receiver()
        self.scanning = True
        self.track_selected_mode = False
        self._discovery_attempts = 0
        self._load_paired_devices()
        self._attempt_start_discovery()

        if self.ble_callback is None:
            self.ble_callback = BLEScanCallback(self)
        try:
            self.adapter.stopLeScan(self.ble_callback)
        except Exception:
            pass
        try:
            ble_started = bool(self.adapter.startLeScan(self.ble_callback))
            self._log(f"BLE scan started={ble_started}")
        except Exception as exc:
            self._log(f"BLE start error: {exc}")

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
                self._log(f"Stop scan error: {exc}")
        # Keep BLE scan alive for selected device tracking after pressing Stop.
        if self.selected_address:
            self.track_selected_mode = True
            self._ensure_ble_tracking()
            self.scanning = False
            self._status("Full scan stopped, tracking selected device")
            return

        if IS_ANDROID and self.adapter is not None:
            self._stop_ble()
            self.track_selected_mode = False
        self.scanning = False
        self._status("Scan stopped")

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
            self._log(f"BLE tracking started={started} target={self.selected_address}")
        except Exception as exc:
            self._log(f"BLE tracking error: {exc}")

    def _stop_ble(self):
        if not IS_ANDROID or self.adapter is None or self.ble_callback is None:
            return
        try:
            self.adapter.stopLeScan(self.ble_callback)
        except Exception as exc:
            self._log(f"Stop BLE error: {exc}")

    def shutdown(self):
        self.track_selected_mode = False
        if IS_ANDROID and self.adapter is not None:
            self._stop_ble()
            try:
                if self.adapter.isDiscovering():
                    self.adapter.cancelDiscovery()
            except Exception as exc:
                self._log(f"Shutdown discovery stop error: {exc}")
        self.scanning = False
        self._status("Scan stopped")
        if self.receiver is not None:
            self.receiver.stop()
            self.receiver = None
