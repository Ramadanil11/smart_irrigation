import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 1. Konfigurasi Database (Perbaikan MySQL untuk Railway)
db_url = os.getenv("mysql://root:iSEQEeYOZUjEzUkBiShOSKACGOqguOuK@mysql.railway.internal:3306/railway")
if db_url and db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    id = db.Column(db.Integer, primary_key=True)
    moisture_level = db.Column(db.Float)
    water_level = db.Column(db.Float)
    pump_status = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PumpSchedule(db.Model):
    __tablename__ = 'pump_schedules'
    id = db.Column(db.Integer, primary_key=True)
    on_time = db.Column(db.String(10))
    off_time = db.Column(db.String(10))
    is_active = db.Column(db.Boolean, default=True)

class PumpControl(db.Model):
    __tablename__ = 'pump_control'
    id = db.Column(db.Integer, primary_key=True)
    manual_target = db.Column(db.String(10))
    pause_until = db.Column(db.DateTime, nullable=True)

# 2. Inisialisasi Database (Otomatis membuat tabel jika belum ada)
with app.app_context():
    db.create_all()

# --- API ENDPOINTS ---

@app.route('/api/sensor/latest', methods=['GET'])
def get_latest():
    data = SensorData.query.order_by(SensorData.created_at.desc()).first()
    if data:
        return jsonify({
            "moisture_level": data.moisture_level,
            "water_level": data.water_level,
            "pump_status": data.pump_status
        })
    # Data default jika tabel masih kosong
    return jsonify({"moisture_level": 0, "water_level": 0, "pump_status": "OFF"})

@app.route('/api/sensor/history', methods=['GET'])
def get_history():
    # Mengambil 7 data terakhir untuk chart
    history = SensorData.query.order_by(SensorData.created_at.desc()).limit(7).all()
    if not history:
        return jsonify([]) # Kembalikan list kosong jika data tidak ada
        
    return jsonify([{
        "moisture": h.moisture_level,
        "water": h.water_level,
        "time": h.created_at.strftime('%H:%M')
    } for h in reversed(history)])

@app.route('/api/control/update', methods=['POST'])
def update_control():
    # Gunakan .get() atau request.json untuk fleksibilitas
    ctype = request.form.get('type') or request.json.get('type')
    target = request.form.get('target') or request.json.get('target')
    
    ctrl = PumpControl.query.first() or PumpControl()
    if ctype == 'manual':
        ctrl.manual_target = target
    
    db.session.add(ctrl)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/schedule/add', methods=['POST'])
def add_schedule():
    on_t = request.form.get('on_time') or request.json.get('on_time')
    off_t = request.form.get('off_time') or request.json.get('off_time')
    
    sched = PumpSchedule.query.first() or PumpSchedule()
    sched.on_time = on_t
    sched.off_time = off_t
    
    db.session.add(sched)
    db.session.commit()
    return jsonify({"status": "schedule updated"})

# ENDPOINT TAMBAHAN: Untuk test input data dari Postman/Hardware
@app.route('/api/sensor/add', methods=['POST'])
def add_sensor_data():
    try:
        moisture = request.form.get('moisture') or request.json.get('moisture')
        water = request.form.get('water') or request.json.get('water')
        pump = request.form.get('pump') or request.json.get('pump', 'OFF')
        
        new_data = SensorData(
            moisture_level=float(moisture),
            water_level=float(water),
            pump_status=pump
        )
        db.session.add(new_data)
        db.session.commit()
        return jsonify({"status": "data added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    # Railway mengharuskan host 0.0.0.0 agar bisa diakses luar
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)