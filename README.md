# NearFar Audio BT

แอป Android (Kivy + Python) สำหรับสแกนอุปกรณ์ Bluetooth และสลับเสียงอัตโนมัติตามค่า RSSI ของอุปกรณ์ที่เลือก (เช่น สมาร์ตวอทช์)

## ความสามารถหลัก
- สแกน Bluetooth ทั้ง Classic และ BLE
- แสดงรายการอุปกรณ์พร้อม RSSI และระยะทางโดยประมาณ
- เลือกอุปกรณ์เป้าหมายจากรายการ
- ติดตามค่า RSSI ของอุปกรณ์ที่เลือกต่อเนื่อง
- สลับเอาต์พุตเสียงระหว่างลำโพงเครื่องและ Bluetooth ตาม threshold
- มีหน้า Log สำหรับตรวจสอบสถานะการทำงาน

## โครงสร้างไฟล์หลัก
- `main.py` UI หลักและ flow การทำงานของแอป
- `scan.py` logic การสแกน Bluetooth และ tracking
- `pullrssi.py` จัดเก็บ/คำนวณข้อมูล RSSI
- `output.py` จัดการ audio output
- `service_foreground.py` งาน background/foreground service
- `buildozer.spec` config สำหรับ build Android

## วิธีใช้งาน (พัฒนา)
1. สร้าง virtual environment และติดตั้ง dependency ของ Kivy/Android
2. รันแอปในอุปกรณ์ Android ที่เปิด Bluetooth
3. เลือกอุปกรณ์จาก dropdown แล้วติดตามค่า RSSI

## หมายเหตุ
- โปรเจกต์นี้ออกแบบให้ทำงานบน Android เป็นหลัก
- ต้องอนุญาตสิทธิ์ Bluetooth/Location/Notification ให้ครบเพื่อการสแกนที่ถูกต้อง
