import json
import os
import traceback
from time import sleep

from app_platform import App_Platform

IS_ANDROID = App_Platform.is_android()

if IS_ANDROID:
    from jnius import PythonJavaClass, autoclass, java_method

    PythonService = autoclass("org.kivy.android.PythonService")
    BuildVersion = autoclass("android.os.Build$VERSION")
    NotificationChannel = autoclass("android.app.NotificationChannel")
    NotificationManager = autoclass("android.app.NotificationManager")
    NotificationBuilder = autoclass("android.app.Notification$Builder")
    PendingIntent = autoclass("android.app.PendingIntent")
    Intent = autoclass("android.content.Intent")
    Context = autoclass("android.content.Context")
    Log = autoclass("android.util.Log")
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    AudioManager = autoclass("android.media.AudioManager")


def _log(msg):
    Log.i("BLERSSI_SERVICE", str(msg))


class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]
    __javacontext__ = "app"

    def __init__(self, rssi_store):
        super().__init__()
        self.rssi_store = rssi_store

    @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
    def onLeScan(self, device, rssi, _scan_record):
        if device is None:
            return
        address = device.getAddress()
        if address is None:
            return
        self.rssi_store[address] = int(rssi)


def start_foreground_notification():
    service = PythonService.mService
    context = service.getApplicationContext()
    channel_id = "blerssi_bg"
    channel_name = "Bluetooth RSSI Background"

    if BuildVersion.SDK_INT >= 26:
        channel = NotificationChannel(
            channel_id,
            channel_name,
            NotificationManager.IMPORTANCE_LOW,
        )
        nm = context.getSystemService(Context.NOTIFICATION_SERVICE)
        nm.createNotificationChannel(channel)
        builder = NotificationBuilder(context, channel_id)
    else:
        builder = NotificationBuilder(context)

    package_manager = context.getPackageManager()
    activity_intent = package_manager.getLaunchIntentForPackage(
        context.getPackageName()
    )
    if activity_intent is None:
        activity_intent = Intent()
    activity_intent.setFlags(
        Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_NEW_TASK
    )
    pending_flags = PendingIntent.FLAG_UPDATE_CURRENT
    if BuildVersion.SDK_INT >= 23:
        pending_flags |= PendingIntent.FLAG_IMMUTABLE
    pending_intent = PendingIntent.getActivity(
        context, 0, activity_intent, pending_flags
    )

    builder.setContentTitle("Bluetooth RSSI Running")
    builder.setContentText("Background tracking is active")
    builder.setSmallIcon(context.getApplicationInfo().icon)
    builder.setOngoing(True)
    builder.setContentIntent(pending_intent)

    service.startForeground(1001, builder.build())


def get_state_file_path(context):
    return os.path.join(context.getFilesDir().getAbsolutePath(), "blerssi_state.json")


def read_state(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def apply_audio_route(am, rssi, threshold):
    if rssi > threshold:
        am.setMode(AudioManager.MODE_IN_COMMUNICATION)
        am.setBluetoothScoOn(False)
        am.stopBluetoothSco()
        am.setSpeakerphoneOn(True)
        return "speaker"
    am.setSpeakerphoneOn(False)
    am.setMode(AudioManager.MODE_NORMAL)
    am.setBluetoothScoOn(False)
    am.stopBluetoothSco()
    return "bluetooth"


def main():
    try:
        service = PythonService.mService
        service.setAutoRestartService(True)
        start_foreground_notification()
        _log("Foreground service started")
        context = service.getApplicationContext()
        adapter = BluetoothAdapter.getDefaultAdapter()
        am = context.getSystemService(Context.AUDIO_SERVICE)
        state_file = get_state_file_path(context)
        rssi_store = {}
        callback = BLEScanCallback(rssi_store)
        last_route = None
        last_rssi = None

        if adapter is None:
            _log("Bluetooth adapter not found in service")
        elif not adapter.isEnabled():
            _log("Bluetooth is OFF in service")
        else:
            try:
                started = bool(adapter.startLeScan(callback))
                _log(f"Service BLE scan started={started}")
            except Exception as exc:
                _log(f"Service BLE start error: {exc}")

        while True:
            state = read_state(state_file)
            selected_address = state.get("selected_address")
            threshold = int(state.get("rssi_threshold", -50))

            if selected_address and selected_address in rssi_store and am is not None:
                rssi = int(rssi_store[selected_address])
                route = apply_audio_route(am, rssi, threshold)
                if route != last_route or rssi != last_rssi:
                    _log(
                        f"Applied route={route} selected={selected_address} "
                        f"rssi={rssi} threshold={threshold}"
                    )
                last_route = route
                last_rssi = rssi

            sleep(1)
    except Exception as exc:
        _log(f"Service error: {exc}")
        _log(traceback.format_exc())
        while True:
            sleep(5)


if __name__ == "__main__":
    main()
