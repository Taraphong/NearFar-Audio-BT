from app_platform import App_Platform

IS_ANDROID = App_Platform.is_android()

if IS_ANDROID:
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Context = autoclass("android.content.Context")
    Intent = autoclass("android.content.Intent")
    PowerManager = autoclass("android.os.PowerManager")
    ServiceBg = autoclass("com.example.nearfar.ServiceBg")
    Uri = autoclass("android.net.Uri")


class AndroidLifecycleHelper:
    def __init__(self, on_log):
        self.on_log = on_log
        self.bg_wakelock = None

    def acquire_wakelock(self):
        if not IS_ANDROID or self.bg_wakelock is not None:
            return
        try:
            activity = PythonActivity.mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            tag = "blerssi:background"
            self.bg_wakelock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, tag)
            self.bg_wakelock.acquire()
            self.on_log("Background wakelock acquired")
        except Exception as exc:
            self.on_log(f"Wakelock acquire error: {exc}")

    def release_wakelock(self):
        if self.bg_wakelock is None:
            return
        try:
            if self.bg_wakelock.isHeld():
                self.bg_wakelock.release()
            self.on_log("Background wakelock released")
        except Exception as exc:
            self.on_log(f"Wakelock release error: {exc}")
        finally:
            self.bg_wakelock = None

    def request_ignore_battery_optimizations(self):
        if not IS_ANDROID:
            return
        try:
            activity = PythonActivity.mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            package_name = activity.getPackageName()
            if pm is not None and pm.isIgnoringBatteryOptimizations(package_name):
                self.on_log("Battery optimization already ignored")
                return
            intent = Intent("android.settings.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS")
            intent.setData(Uri.parse(f"package:{package_name}"))
            activity.startActivity(intent)
            self.on_log("Requested ignore battery optimization")
        except Exception as exc:
            self.on_log(f"Battery optimization request error: {exc}")

    def start_foreground_service(self):
        if not IS_ANDROID:
            return
        missing_permissions = App_Platform.missing_foreground_service_permissions()
        if missing_permissions:
            self.on_log(
                "Foreground service permission missing: "
                + ", ".join(missing_permissions)
            )
            App_Platform.request_permissions(missing_permissions)
            return
        try:
            activity = PythonActivity.mActivity
            # python-for-android service classes expose static start(context, arg)
            # and handle proper startForegroundService/startService internally.
            ServiceBg.start(activity, "")
            self.on_log("Foreground service started (ServiceBg.start)")
        except Exception as exc:
            self.on_log(f"Foreground service start error (start): {exc}")
