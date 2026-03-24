# NearFar Audio BT

**NearFar Audio BT** is an Android application built with **Kivy + Python** for intelligent audio output management. It automatically toggles audio between the device speaker and Bluetooth peripherals based on the Received Signal Strength Indicator (RSSI) of a selected target device.

##  Key Features

* **Hybrid Bluetooth Scanning:** Supports discovery of both Bluetooth Classic and BLE devices.
* **Real-time Proximity Tracking:** Displays nearby devices with RSSI values and estimated distance calculations.
* **Smart Audio Switching:** Automatically routes audio based on predefined RSSI thresholds.
* **Foreground Service:** Ensures seamless background operation and signal tracking.
* **Activity Logs:** Built-in console for monitoring connection status and signal fluctuations.

<<<<<<< HEAD
##  Core Architecture

* **`main.py`**: Handles User Interface and primary application flow.
* **`scan.py`**: Manages device discovery and continuous tracking logic.
* **`pullrssi.py`**: Handles data processing, signal filtering, and distance estimation.
* **`output.py`**: Interfaces with Android Audio Manager to reroute audio streams.
* **`service_foreground.py`**: Implements the Android Foreground Service.
* **`buildozer.spec`**: Configuration for Android deployment and permissions.

##  Deployment & Usage

1.  **Environment:** Set up Python with Kivy and Buildozer installed.
2.  **Configuration:** Ensure all required Android permissions are declared in the spec file.
3.  **Deployment:** Run `buildozer -v android debug` to generate the APK.
4.  **Initialization:** Grant Bluetooth and Location/GPS permissions on the device.
5.  **Operation:** Select your target device from the dropdown to begin proximity-based automation.

---

##  หมายเหตุ / Notes
- โปรเจกต์นี้ออกแบบมาเพื่อใช้งานบน **Android** เป็นหลัก (This project is primarily designed for Android).
- การสแกน Bluetooth ใน Android เวอร์ชันใหม่จำเป็นต้องเปิด **Location/GPS** ตลอดเวลา (Bluetooth scanning requires GPS/Location to be enabled on modern Android versions).
