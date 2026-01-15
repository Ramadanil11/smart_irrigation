# GitHub Copilot Chat Assistant
import os
from datetime import datetime, time, timedelta

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# App & CORS
app = Flask(__name__)
CORS(app)

# Database configuration
# Prefer an existing DATABASE_URL (Railway/Heroku style), otherwise build from components.
db_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
if not db_url:
    # Build from components if separate env vars exist
    mysql_user = os.getenv("MYSQL_USER", os.getenv("DB_USER", "root"))
    mysql_password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
    mysql_host = os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
    mysql_port = os.getenv("MYSQL_PORT", os.getenv("DB_PORT", "3306"))
    mysql_db = os.getenv("MYSQL_DB", os.getenv("DB_NAME", "railway"))
    db_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"

# If someone provided a mysql:// URL, SQLAlchemy expects mysql+pymysql:// for PyMySQL driver
if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --- DATABASE MODELS ---
class SensorData(db.Model):
    __tablename__ = "sensor_data"
    id = db.Column(db.Integer, primary_key=True)
    moisture_level = db.Column(db.Float, nullable=False)
    water_level = db.Column(db.Float, nullable=False)
    pump_status = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PumpSchedule(db.Model):
    __tablename__ = "pump_schedules"
    id = db.Column(db.Integer, primary_key=True)
    on_time = db.Column(db.String(8))   # expected "HH:MM" or "HH:MM:SS"
    off_time = db.Column(db.String(8))
    is_active = db.Column(db.Boolean, default=True)


class PumpControl(db.Model):
    __tablename__ = "pump_control"
    id = db.Column(db.Integer, primary_key=True)
    manual_target = db.Column(db.String(10), default="OFF")  # "ON" or "OFF" or other
    pause_until = db.Column(db.DateTime, nullable=True)


# Create tables if not exist
with app.app_context():
    db.create_all()


# --- Helpers ---
def parse_time_str(t: str) -> time:
    """Parse "HH:MM" or "HH:MM:SS" into datetime.time; raises ValueError if invalid."""
    if not t:
        raise ValueError("empty time")
    parts = t.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        h, m = parts
        s = 0
    elif len(parts) == 3:
        h, m, s = parts
    else:
        raise ValueError("invalid time format")
    return time(h, m, s)


def is_now_between(on_str: str, off_str: str, now_dt: datetime) -> bool:
    """Check if now (datetime) is between on_time and off_time (strings). Handles overnight ranges."""
    try:
        on_t = parse_time_str(on_str)
        off_t = parse_time_str(off_str)
    except Exception:
        return False

    now_t = now_dt.time()

    if on_t <= off_t:
        return on_t <= now_t <= off_t
    else:
        # overnight: e.g., on=22:00 off=06:00
        return now_t >= on_t or now_t <= off_t


# --- API ENDPOINTS ---


@app.route("/api/sensor/latest", methods=["GET"])
def get_latest():
    data = SensorData.query.order_by(SensorData.created_at.desc()).first()
    if data:
        return jsonify({
            "moisture_level": data.moisture_level,
            "water_level": data.water_level,
            "pump_status": data.pump_status,
            "created_at": data.created_at.isoformat()
        }), 200
    return jsonify({"moisture_level": 0, "water_level": 0, "pump_status": "OFF"}), 200


@app.route("/api/sensor/history", methods=["GET"])
def get_history():
    limit = int(request.args.get("limit", 7))
    history = SensorData.query.order_by(SensorData.created_at.desc()).limit(limit).all()
    if not history:
        return jsonify([]), 200

    # Return oldest -> newest
    return jsonify([{
        "moisture": h.moisture_level,
        "water": h.water_level,
        "pump_status": h.pump_status,
        "time": h.created_at.strftime("%H:%M")
    } for h in reversed(history)]), 200


@app.route("/api/control/update", methods=["POST"])
def update_control():
    data = request.form.to_dict() or request.get_json(silent=True) or {}
    ctype = data.get("type")
    target = data.get("target")
    minutes = data.get("minutes")

    ctrl = PumpControl.query.first()
    if not ctrl:
        ctrl = PumpControl(manual_target="OFF")
        db.session.add(ctrl)

    if ctype == "manual":
        # set manual target and clear pause
        if target:
            ctrl.manual_target = str(target).upper()
        ctrl.pause_until = None

    elif ctype == "pause":
        try:
            mins = int(minutes or 0)
            ctrl.pause_until = datetime.utcnow() + timedelta(minutes=mins)
        except Exception:
            return jsonify({"error": "invalid minutes"}), 400

    db.session.commit()
    return jsonify({"status": "success"}), 200


@app.route("/api/schedule/add", methods=["POST"])
def add_schedule():
    data = request.form.to_dict() or request.get_json(silent=True) or {}
    on_t = data.get("on_time")
    off_t = data.get("off_time")

    if not on_t or not off_t:
        return jsonify({"error": "on_time and off_time are required"}), 400

    # Deactivate all existing schedules and add a new one (same logic as original)
    PumpSchedule.query.update({"is_active": False})
    new_sched = PumpSchedule(on_time=on_t, off_time=off_t, is_active=True)
    db.session.add(new_sched)
    db.session.commit()
    return jsonify({"status": "schedule added"}), 201


@app.route("/api/sensor/add", methods=["POST"])
def add_sensor_data():
    # Simple endpoint for manual data insertion (Postman)
    data = request.form.to_dict() or request.get_json(silent=True) or {}
    try:
        moisture = float(data.get("moisture", 0))
        water = float(data.get("water", 0))
        pump = data.get("pump", "OFF")
    except Exception:
        return jsonify({"error": "invalid numeric values"}), 400

    new_data = SensorData(
        moisture_level=moisture,
        water_level=water,
        pump_status=str(pump).upper()
    )
    db.session.add(new_data)
    db.session.commit()
    return jsonify({"status": "data added"}), 201


@app.route("/api/sensor/save", methods=["POST"])
def save_sensor_data():
    # Endpoint intended for hardware (ESP32)
    data = request.form.to_dict() or request.get_json(silent=True) or {}
    try:
        moisture = float(data.get("moisture", data.get("moisture_level", 0)))
        water = float(data.get("water", data.get("water_level", 0)))
    except Exception:
        return jsonify({"error": "invalid numeric values"}), 400

    now = datetime.utcnow()

    # Load control & schedule
    ctrl = PumpControl.query.first()
    target_status = "OFF"

    # 1) manual target takes precedence unless paused
    if ctrl and ctrl.manual_target:
        target_status = ctrl.manual_target.upper()

    # 2) if pause_until present and not expired -> force OFF
    if ctrl and ctrl.pause_until:
        if now < ctrl.pause_until:
            target_status = "OFF"
        else:
            # pause expired -> clear it
            ctrl.pause_until = None
            db.session.add(ctrl)
            db.session.commit()

    # 3) If no manual ON and not paused, check active schedule(s)
    if target_status != "ON":
        active_scheds = PumpSchedule.query.filter_by(is_active=True).all()
        for s in active_scheds:
            if s.on_time and s.off_time and is_now_between(s.on_time, s.off_time, now):
                target_status = "ON"
                break

    # Save sensor data with decided pump command/state
    new_data = SensorData(
        moisture_level=moisture,
        water_level=water,
        pump_status=target_status
    )
    db.session.add(new_data)
    db.session.commit()

    return jsonify({"status": "success", "command": target_status}), 201


if __name__ == "__main__":
    # For local/dev run only. In production (Railway) use the platform's entrypoint.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)