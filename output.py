from time import monotonic
from platfrom import Platform

IS_ANDROID = Platform.is_android()

if IS_ANDROID:
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    AudioManager = autoclass("android.media.AudioManager")
    Context = autoclass("android.content.Context")


class AudioOutputController:
    def __init__(self, on_log):
        self.on_log = on_log
        self.audio_manager = None
        self.current_route = None
        self.pending_route = None
        self.pending_since = None
        self.last_rssi_at = None
        self.last_decision_log_at = 0.0
        self.hysteresis_db = 6
        self.hold_seconds = 2.2
        self.stale_seconds = 6.0

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

    @staticmethod
    def _route_ui(route):
        if route == "speaker":
            return ("play on speaker", (0, 1, 0, 1))
        return ("play on Bluetooth", (1, 0.5, 0, 1))

    def _throttled_log(self, text):
        now = monotonic()
        if now - self.last_decision_log_at >= 1.0:
            self.on_log(text)
            self.last_decision_log_at = now

    def _route_from_rssi(self, rssi, threshold):
        enter_speaker_at = threshold + self.hysteresis_db
        enter_bluetooth_at = threshold - self.hysteresis_db
        if self.current_route is None:
            return ("speaker" if rssi > threshold else "bluetooth"), "initial-threshold"
        if self.current_route == "bluetooth" and rssi >= enter_speaker_at:
            return "speaker", f"crossed-enter-speaker({enter_speaker_at})"
        if self.current_route == "speaker" and rssi <= enter_bluetooth_at:
            return "bluetooth", f"crossed-enter-bluetooth({enter_bluetooth_at})"
        return self.current_route, "inside-hysteresis-band"

    def _apply_route(self, route):
        if route == self.current_route:
            return self._route_ui(route)
        if not IS_ANDROID:
            self.current_route = route
            return self._route_ui(route)
        if self.audio_manager is None:
            return None
        if route == "speaker":
            self.audio_manager.setMode(AudioManager.MODE_IN_COMMUNICATION)
            self.audio_manager.setBluetoothScoOn(False)
            self.audio_manager.stopBluetoothSco()
            self.audio_manager.setSpeakerphoneOn(True)
            self.on_log("Route applied -> speaker")
        else:
            self.audio_manager.setSpeakerphoneOn(False)
            self.audio_manager.setMode(AudioManager.MODE_NORMAL)
            # For media playback route, do not force SCO (SCO is for call audio).
            self.audio_manager.setBluetoothScoOn(False)
            self.audio_manager.stopBluetoothSco()
            self.on_log("Route applied -> bluetooth(auto)")
        self.current_route = route
        return self._route_ui(route)

    def apply_output_for_rssi(self, rssi, threshold):
        if not isinstance(rssi, int):
            return None
        now = monotonic()
        self.last_rssi_at = now

        target_route, reason = self._route_from_rssi(rssi, threshold)
        self._throttled_log(
            f"Decision: route={target_route} rssi={rssi} threshold={threshold} reason={reason}"
        )
        if self.current_route is None:
            return self._apply_route(target_route)

        if target_route == self.current_route:
            self.pending_route = None
            self.pending_since = None
            return self._route_ui(self.current_route)

        if self.pending_route != target_route:
            self.pending_route = target_route
            self.pending_since = now
            self._throttled_log(
                f"Debounce start: pending={target_route} hold={self.hold_seconds:.1f}s"
            )
            return self._route_ui(self.current_route)

        elapsed = now - (self.pending_since or now)
        if elapsed < self.hold_seconds:
            return self._route_ui(self.current_route)

        try:
            self.on_log(
                f"Debounce commit: switch {self.current_route}->{target_route} after {elapsed:.2f}s"
            )
            ui_state = self._apply_route(target_route)
            self.pending_route = None
            self.pending_since = None
            return ui_state
        except Exception as exc:
            self.on_log(f"Output route error: {exc}")
            return None

    def apply_stale_fallback(self):
        if self.current_route is None or self.last_rssi_at is None:
            return None
        age = monotonic() - self.last_rssi_at
        if age < self.stale_seconds:
            return None
        if self.current_route == "bluetooth":
            return self._route_ui(self.current_route)
        self.on_log(
            f"Stale RSSI timeout ({age:.2f}s >= {self.stale_seconds:.1f}s), fallback to bluetooth"
        )
        self.pending_route = None
        self.pending_since = None
        return self._apply_route("bluetooth")
