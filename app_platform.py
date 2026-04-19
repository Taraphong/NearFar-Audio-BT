import os
import sys

try:
    from kivy.utils import platform as kivy_platform
except Exception:
    kivy_platform = None


platform = kivy_platform or ("android" if "ANDROID_ARGUMENT" in os.environ else sys.platform)


def _log(message):
    text = str(message)
    if platform != "android":
        print(text)
        return
    try:
        from jnius import autoclass

        autoclass("android.util.Log").i("BLERSSI_APP", text)
    except Exception:
        print(text)


class App_Platform:
    MANIFEST_ONLY_PERMISSIONS = [
        "android.permission.FOREGROUND_SERVICE",
        "android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE",
    ]

    @staticmethod
    def is_android():
        if platform != "android":
            return False
        try:
            from android import api_version

            _log(f"ANDROID API VERSION: {api_version}")
        except Exception as exc:
            _log(f"Unable to read Android API version: {exc}")
        return True

    @staticmethod
    def sdk_int():
        if not App_Platform.is_android():
            return 0
        try:
            from jnius import autoclass

            return int(autoclass("android.os.Build$VERSION").SDK_INT)
        except Exception as exc:
            _log(f"Unable to read SDK_INT: {exc}")
            return 0

    @staticmethod
    def bluetooth_runtime_permissions():
        sdk = App_Platform.sdk_int()
        permissions = []
        if sdk >= 31:
            permissions.extend(
                [
                    "android.permission.BLUETOOTH_SCAN",
                    "android.permission.BLUETOOTH_CONNECT",
                ]
            )
        else:
            permissions.extend(
                [
                    "android.permission.ACCESS_FINE_LOCATION",
                    "android.permission.ACCESS_COARSE_LOCATION",
                ]
            )
        return permissions

    @staticmethod
    def foreground_service_runtime_permissions():
        permissions = []
        if App_Platform.sdk_int() >= 33:
            permissions.append("android.permission.POST_NOTIFICATIONS")
        return permissions

    @staticmethod
    def _missing_permissions(permissions):
        if not App_Platform.is_android():
            return []
        try:
            from android.permissions import check_permission

            return [name for name in permissions if not check_permission(name)]
        except Exception as exc:
            _log(f"Permission check error: {exc}")
            return list(permissions)

    @staticmethod
    def request_permissions(permissions=None, callback=None):
        if not App_Platform.is_android():
            return []
        requested = permissions or (
            App_Platform.bluetooth_runtime_permissions()
            + App_Platform.foreground_service_runtime_permissions()
        )
        missing = App_Platform._missing_permissions(requested)
        if not missing:
            return []
        try:
            from android.permissions import request_permissions

            request_permissions(missing, callback)
        except Exception as exc:
            _log(f"Permission request error: {exc}")
        return missing

    @staticmethod
    def missing_bluetooth_permissions():
        return App_Platform._missing_permissions(
            App_Platform.bluetooth_runtime_permissions()
        )

    @staticmethod
    def missing_foreground_service_permissions():
        return App_Platform._missing_permissions(
            App_Platform.foreground_service_runtime_permissions()
        )

    @staticmethod
    def is_location_service_enabled():
        if not App_Platform.is_android():
            return False
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            LocationManager = autoclass("android.location.LocationManager")

            activity = PythonActivity.mActivity
            manager = activity.getSystemService(Context.LOCATION_SERVICE)
            if manager is None:
                return False
            gps_enabled = bool(manager.isProviderEnabled(LocationManager.GPS_PROVIDER))
            network_enabled = bool(
                manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
            )
            return gps_enabled or network_enabled
        except Exception as exc:
            _log(f"Location service check error: {exc}")
            return False
