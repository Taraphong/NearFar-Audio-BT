from kivy.utils import platform

IS_ANDROID = platform == "android"

if IS_ANDROID:
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    AudioManager = autoclass("android.media.AudioManager")
    Context = autoclass("android.content.Context")


class AudioOutputController:
    def __init__(self, on_log):
        self.on_log = on_log
        self.audio_manager = None

    def initialize(self):
        if not IS_ANDROID:
            return False
        try:
            activity = PythonActivity.mActivity
            self.audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
            return self.audio_manager is not None
        except Exception as exc:
            self.on_log(f"Audio init error: {exc}")
            return False

    def apply_output_for_rssi(self, rssi, threshold):
        if not IS_ANDROID:
            if rssi > threshold:
                return ("play on speaker", (0, 1, 0, 1))
            return ("play on Bluetooth", (1, 0.5, 0, 1))
        if self.audio_manager is None:
            return None
        try:
            self.on_log(f"Route decision: rssi={rssi} threshold={threshold}")
            if rssi > threshold:
                self.audio_manager.setMode(AudioManager.MODE_IN_COMMUNICATION)
                self.audio_manager.setBluetoothScoOn(False)
                self.audio_manager.stopBluetoothSco()
                self.audio_manager.setSpeakerphoneOn(True)
                self.on_log("Forcing Speaker: ON")
                return ("play on speaker", (0, 1, 0, 1))
            self.audio_manager.setSpeakerphoneOn(False)
            self.audio_manager.setMode(AudioManager.MODE_NORMAL)
            # For media playback route, do not force SCO (SCO is for call audio).
            self.audio_manager.setBluetoothScoOn(False)
            self.audio_manager.stopBluetoothSco()
            self.on_log("Forcing Speaker: OFF (Auto Route)")
            return ("play on Bluetooth", (1, 0.5, 0, 1))
        except Exception as exc:
            self.on_log(f"Output route error: {exc}")
            return None
