from kivy.utils import platform


class App_Platform:
    @staticmethod
    def is_android():
        if platform == "android":
            return platform
        else:
            pass


class permissions:
    @staticmethod
    def _sdk_int():
        if not Platform.is_android():
            return 0
        try:
            from jnius import autoclass

            BuildVersion = autoclass("android.os.Build$VERSION")
            return int(BuildVersion.SDK_INT)
        except Exception:
            return 0

    @staticmethod
    def _activity():
        if not Platform.is_android():
            return None
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            return PythonActivity.mActivity
        except Exception:
            return None

    @staticmethod
    def bluetooth_permissions():
        sdk = Platform._sdk_int()
        if sdk >= 31:
            return [
                "android.permission.BLUETOOTH_SCAN",
                "android.permission.BLUETOOTH_CONNECT",
            ]
        return [
            "android.permission.BLUETOOTH",
            "android.permission.BLUETOOTH_ADMIN",
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
        ]

    @staticmethod
    def foreground_service_permissions():
        permissions = [
            "android.permission.FOREGROUND_SERVICE",
        ]
        if Platform._sdk_int() >= 34:
            permissions.append("android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE")
        return permissions

    @staticmethod
    def optional_runtime_permissions():
        permissions = [
            "android.permission.ACCESS_BACKGROUND_LOCATION",
            "android.permission.MODIFY_AUDIO_SETTINGS",
            "android.permission.POST_NOTIFICATIONS",
        ]
        if Platform._sdk_int() < 29:
            return [
                perm
                for perm in permissions
                if perm != "android.permission.ACCESS_BACKGROUND_LOCATION"
            ]
        if Platform._sdk_int() < 33:
            return [
                perm
                for perm in permissions
                if perm != "android.permission.POST_NOTIFICATIONS"
            ]
        return permissions

    @staticmethod
    def requested_permissions():
        return (
            Platform.bluetooth_permissions()
            + Platform.foreground_service_permissions()
            + Platform.optional_runtime_permissions()
        )

    @staticmethod
    def has_permission(permission_name):
        if not Platform.is_android():
            return True
        try:
            from jnius import autoclass

            PackageManager = autoclass("android.content.pm.PackageManager")
            activity = Platform._activity()
            if activity is None:
                return False
            granted = activity.checkSelfPermission(permission_name)
            return int(granted) == int(PackageManager.PERMISSION_GRANTED)
        except Exception:
            return False

    @staticmethod
    def missing_permissions(permission_names):
        if not Platform.is_android():
            return []
        return [perm for perm in permission_names if not Platform.has_permission(perm)]

    @staticmethod
    def missing_bluetooth_permissions():
        return Platform.missing_permissions(Platform.bluetooth_permissions())

    @staticmethod
    def missing_foreground_service_permissions():
        return Platform.missing_permissions(Platform.foreground_service_permissions())

    @staticmethod
    def request_permissions(permission_names=None):
        if not Platform.is_android():
            return
        try:
            from android.permissions import request_permissions  # type: ignore

            request_permissions(permission_names or Platform.requested_permissions())
        except Exception:
            return

    @staticmethod
    def is_location_service_enabled():
        if not Platform.is_android():
            return False
        try:
            from jnius import autoclass

            Context = autoclass("android.content.Context")
            LocationManager = autoclass("android.location.LocationManager")
            activity = Platform._activity()
            if activity is None:
                return False
            location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
            if location_manager is None:
                return False
            gps_enabled = bool(
                location_manager.isProviderEnabled(LocationManager.GPS_PROVIDER)
            )
            network_enabled = bool(
                location_manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
            )
            return gps_enabled or network_enabled
        except Exception:
            return False
