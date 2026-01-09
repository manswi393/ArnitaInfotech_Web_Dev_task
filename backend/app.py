from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hospital_secret'
CORS(app)   # Allow frontend to connect

# ================= MAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'     # change
app.config['MAIL_PASSWORD'] = 'your_app_password'        # change

mail = Mail(app)

# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS doctors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        department TEXT,
        email TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        email TEXT,
        doctor_id INTEGER,
        date TEXT,
        time TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    # Insert default admin (only once)
    cur.execute("SELECT * FROM admins")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO admins(username,password) VALUES(?,?)",
            ("admin", generate_password_hash("admin123"))
        )

    db.commit()
    db.close()

init_db()

# ================= ADMIN LOGIN =================
@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM admins WHERE username=?", (data['username'],))
    admin = cur.fetchone()
    db.close()

    if admin and check_password_hash(admin['password'], data['password']):
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid credentials"}), 401

# ================= BOOK APPOINTMENT =================
@app.route("/appointment/book", methods=["POST"])
def book_appointment():
    data = request.json

    try:
        date_obj = datetime.strptime(data['date'], "%Y-%m-%d")
        if date_obj.weekday() == 6:
            return jsonify({"error": "Appointments not available on Sunday"}), 400
    except:
        return jsonify({"error": "Invalid date format"}), 400

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    INSERT INTO appointments(patient_name,email,doctor_id,date,time)
    VALUES(?,?,?,?,?)
    """, (
        data['name'],
        data['email'],
        data['doctor_id'],
        data['date'],
        data['time']
    ))

    db.commit()
    db.close()

    send_doctor_email(data['doctor_id'])
    return jsonify({"message": "Appointment request submitted successfully"})

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard", methods=["GET"])
def dashboard():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM doctors")
    doctors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Pending'")
    pending = cur.fetchone()[0]

    cur.execute("""
    SELECT a.id, patient_name, d.name as doctor, date, time, status
    FROM appointments a
    LEFT JOIN doctors d ON a.doctor_id = d.id
    ORDER BY date DESC
    """)

    appointments = [dict(row) for row in cur.fetchall()]
    db.close()

    return jsonify({
        "stats": {
            "doctors": doctors,
            "appointments": total,
            "pending": pending
        },
        "appointments": appointments
    })

# ================= DOCTOR ACTION =================
@app.route("/doctor/confirm/<int:id>")
def confirm(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE appointments SET status='Confirmed' WHERE id=?", (id,))
    db.commit()
    db.close()
    return "Appointment Confirmed Successfully"

@app.route("/doctor/reject/<int:id>")
def reject(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE appointments SET status='Rejected' WHERE id=?", (id,))
    db.commit()
    db.close()
    return "Appointment Rejected"

# ================= EMAIL =================
def send_doctor_email(doctor_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT email FROM doctors WHERE id=?", (doctor_id,))
        doctor = cur.fetchone()
        db.close()

        if doctor:
            msg = Message(
                subject="New Appointment Request",
                recipients=[doctor['email']]
            )
            msg.body = (
                "You have a new appointment request.\n\n"
                "Please login to the system to confirm or reject."
            )
            mail.send(msg)
    except Exception as e:
        print("Email Error:", e)

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
