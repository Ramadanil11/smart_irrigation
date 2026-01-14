import os
import mysql.connector
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()

# Middleware CORS agar Flutter bisa akses
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- KONSTRUKTOR KONEKSI DATABASE ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('mysql.railway.internal'),
        user=os.getenv('root'),
        password=os.getenv('iSEQEeYOZUjEzUkBiShOSKACGOqguOuK'),
        database=os.getenv('railway'),
        port=int(os.getenv('3306', 3306)),
        autocommit=True
    )

# 1. ENDPOINT: MONITORING (Ambil data sensor terbaru)
@app.get("/api/sensor/latest")
async def get_latest_sensor():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT moisture_level, water_level, pump_status FROM sensor_data ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row if row else {"moisture_level": 0, "water_level": 0, "pump_status": "OFF"}
    finally:
        db.close()

# 2. ENDPOINT: UPDATE KONTROL (Manual & Jeda/Pause)
@app.post("/api/control/update")
async def update_control(type: str = Form(...), target: Optional[str] = Form(None), minutes: Optional[int] = Form(None)):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        if type == 'manual':
            # Jika manual diubah, hapus status jeda
            cursor.execute("UPDATE pump_control SET manual_target = %s, pause_until = NULL WHERE id = 1", (target,))
        
        elif type == 'pause':
            # Set waktu kapan jeda berakhir
            pause_end = datetime.now() + timedelta(minutes=minutes)
            cursor.execute("UPDATE pump_control SET pause_until = %s WHERE id = 1", (pause_end,))
            
        return {"status": "success"}
    finally:
        db.close()

# 3. ENDPOINT: JADWAL (Tambah/Update Jadwal)
@app.post("/api/schedule/add")
async def add_schedule(on_time: str = Form(...), off_time: str = Form(...)):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        # Nonaktifkan jadwal lama, aktifkan yang baru (Sesuai logika PHP sebelumnya)
        cursor.execute("UPDATE pump_schedules SET is_active = 0")
        cursor.execute("INSERT INTO pump_schedules (on_time, off_time, is_active) VALUES (%s, %s, 1)", (on_time, off_time))
        return {"status": "success"}
    finally:
        db.close()

# 4. LOGIKA UTAMA: DIGUNAKAN OLEH ALAT (ESP32/Hardware)
@app.post("/api/sensor/save")
async def save_sensor_data(moisture: int = Form(...), water: int = Form(...)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    now_time = datetime.now().strftime("%H:%M:%S")
    now_full = datetime.now()

    try:
        # A. Cek Status Kontrol & Jeda
        cursor.execute("SELECT * FROM pump_control WHERE id = 1")
        ctrl = cursor.fetchone()
        
        target_status = ctrl['manual_target'] if ctrl else 'OFF'

        # B. Cek apakah Jeda sudah berakhir
        if ctrl and ctrl['pause_until']:
            if now_full >= ctrl['pause_until']:
                cursor.execute("UPDATE pump_control SET pause_until = NULL WHERE id = 1")
            else:
                target_status = 'OFF' # Masih dalam masa jeda

        # C. Cek Jadwal (Hanya jika tidak sedang dijeda)
        if target_status != 'OFF' or (ctrl and not ctrl['pause_until']):
            cursor.execute("SELECT * FROM pump_schedules WHERE is_active=1 AND %s BETWEEN on_time AND off_time", (now_time,))
            if cursor.fetchone():
                target_status = 'ON'

        # D. Simpan History
        cursor.execute("INSERT INTO sensor_data (moisture_level, water_level, pump_status) VALUES (%s, %s, %s)", 
                       (moisture, water, target_status))
        
        return {"status": "success", "command": target_status}
    finally:
        db.close()
