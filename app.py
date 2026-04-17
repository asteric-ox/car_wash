from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import secrets
import time
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app, supports_credentials=True)

app.secret_key = os.getenv('SECRET_KEY', 'carwash_secret_key')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False, # Change to True if using HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

# =========================
# DATABASE CONNECTION
# =========================
def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASS', 'Delvin@2005'),
        database=os.getenv('DB_NAME', 'postgres'),
        port=os.getenv('DB_PORT', 5432),
        cursor_factory=RealDictCursor
    )

def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fullname VARCHAR(255),
            name VARCHAR(255),  -- For compatibility
            email VARCHAR(255) UNIQUE,
            phone VARCHAR(50) UNIQUE,
            password VARCHAR(255),
            password_hash VARCHAR(255), -- For compatibility
            role ENUM('admin','staff','customer') DEFAULT 'customer',
            status ENUM('active','inactive') DEFAULT 'active',
            stamps INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Vehicles Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            vehicle_number VARCHAR(50),
            vehicle_type VARCHAR(50),
            model VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # Services Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INT AUTO_INCREMENT PRIMARY KEY,
            service_name VARCHAR(100),
            price DECIMAL(10, 2)
        )
        """)

        # Bookings Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NULL,
            customer_name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            vehicle_type VARCHAR(50),
            vehicle_number VARCHAR(50),
            service_package VARCHAR(100),
            appointment_date DATE,
            appointment_time TIME,
            booking_date DATE, -- For compatibility
            booking_time TIME, -- For compatibility
            addons TEXT,
            location VARCHAR(255),
            is_pickup BOOLEAN DEFAULT 0,
            status VARCHAR(50) DEFAULT 'Pending',
            assigned_staff INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_staff) REFERENCES users(id)
        )
        """)

        # Admins Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'staff',
            token VARCHAR(255) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Shop Status Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_status (
            id INT PRIMARY KEY,
            is_busy BOOLEAN DEFAULT 0,
            current_vehicle VARCHAR(255),
            message VARCHAR(255),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Notifications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            message TEXT,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Payments Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT,
            amount DECIMAL(10, 2),
            payment_method VARCHAR(50),
            payment_status VARCHAR(50) DEFAULT 'paid'
        )
        """)

        # Seed data
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            services_data = [
                ('Basic Wash', 200.00),
                ('Normal', 350.00),
                ('Super', 450.00),
                ('Premium', 600.00),
                ('Premium Plus', 800.00)
            ]
            cursor.executemany("INSERT INTO services (service_name, price) VALUES (%s, %s)", services_data)

        cursor.execute("SELECT COUNT(*) FROM shop_status")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO shop_status (id, is_busy, message) VALUES (1, 0, 'Ready to Shine!')")

        cursor.execute("SELECT COUNT(*) FROM admins WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admins (username, password, role) VALUES ('admin', '1234', 'master')")

        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")

# =========================
# UTILITIES
# =========================
ACTIVE_TOKENS = {}

import datetime

def serialize_db_row(row):
    if row is None:
        return None
    for key, value in row.items():
        if isinstance(value, (datetime.date, datetime.datetime, datetime.timedelta)):
            row[key] = str(value)
        elif isinstance(value, datetime.time):
            row[key] = value.strftime('%H:%M:%S')
    return row

def serialize_db_rows(rows):
    return [serialize_db_row(row) for row in rows]

def get_logged_in_user(req):
    token = req.headers.get('X-Admin-Token')
    if not token:
        return None
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE token = %s", (token,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# =========================
# ROUTES (FRONTEND & STATIC)
# =========================
@app.route("/")
def home():
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('public', path)

# =========================
# AUTH ROUTES
# =========================

@app.route("/api/register", methods=["POST"])
@app.route("/register", methods=["POST"]) # Both supported
def register():
    data = request.json
    print(f"DEBUG: Register request data: {data}")
    try:
        fullname = data.get("fullname") or data.get("name") or "User"
        email = data.get("email")
        phone = data.get("phone")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required"}), 400

        # Check if email already exists
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Email already registered. Please login or use a different email."}), 400
        
        # Check if phone already exists (if phone is provided)
        if phone:
            cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({"success": False, "message": "Phone number already registered. Please login or use a different number."}), 400

        hashed_pw = generate_password_hash(password)

        query = """
        INSERT INTO users (fullname, name, email, phone, password, password_hash, role)
        VALUES (%s, %s, %s, %s, %s, %s, 'customer')
        """

        cursor.execute(query, (fullname, fullname, email, phone, hashed_pw, hashed_pw))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"DEBUG: Successfully registered {email}")
        return jsonify({"success": True, "message": "User registered successfully"})
    except psycopg2.IntegrityError as e:
        # Handle any other integrity errors (shouldn't happen with our checks above, but just in case)
        error_msg = str(e)
        if "email" in error_msg.lower():
            return jsonify({"success": False, "message": "Email already registered"}), 400
        elif "phone" in error_msg.lower():
            return jsonify({"success": False, "message": "Phone number already registered"}), 400
        else:
            return jsonify({"success": False, "message": "Registration failed due to duplicate data"}), 400
    except Exception as e:
        print(f"DEBUG: Registration error: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/check-auth", methods=["GET"])
def check_auth():
    if "user_id" in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": session.get("user_id"),
                "name": session.get("user_name"),
                "email": session.get("user_email"),
                "role": session.get("role")
            }
        })
    return jsonify({"authenticated": False}), 401

@app.route("/api/logout", methods=["POST"])
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route("/api/login", methods=["POST"])
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    print(f"DEBUG: Login request for: {data.get('identifier') or data.get('email')}")
    try:
        # identifier can be email or phone from app.js
        identifier = data.get("email") or data.get("identifier")
        password = data.get("password")

        # PERMANENT ADMIN CHECK
        if identifier == "delvindavis031@gmail.com" and password == "Delvin@2005":
            session.permanent = True
            session["user_id"] = 0
            session["user_name"] = "Master Admin"
            session["user_phone"] = "+91 8590624912"
            session["user_email"] = identifier
            session["role"] = "admin"
            
            return jsonify({
                "success": True, 
                "message": "Admin login successful", 
                "user": {
                    "name": "Master Admin", 
                    "phone": "+91 8590624912", 
                    "email": identifier,
                    "role": "admin"
                },
                "user_id": 0,
                "redirect": "/admin.html",
                "role": "admin"
            })

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=%s OR phone=%s", (identifier, identifier))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.permanent = True
            session["user_id"] = user["id"]
            session["user_name"] = user["fullname"] or user["name"] or "User"
            session["user_phone"] = user["phone"]
            session["user_email"] = user["email"]
            session["role"] = user.get("role", "customer")
            
            print(f"DEBUG: Login SUCCESS for {session['user_name']} (Role: {session['role']})")
            
            # Determine redirect URL based on role
            redirect_url = "/index.html"
            if session["role"] in ["admin", "staff"]:
                redirect_url = "/admin.html" if session["role"] == "admin" else "/staff.html"
            
            return jsonify({
                "success": True, 
                "message": "Login successful", 
                "user": {
                    "name": session["user_name"], 
                    "phone": session["user_phone"], 
                    "email": user["email"],
                    "role": session["role"]
                },
                "user_id": user["id"],
                "redirect": redirect_url,
                "role": session["role"]
            })

        print("DEBUG: Login FAILED: Password mismatch for " + identifier)
        return jsonify({"success": False, "message": "Invalid password"}), 401
    except Exception as e:
        print(f"DEBUG: Login ERROR: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# =========================
# BOOKING ROUTES
# =========================

@app.route("/api/book", methods=["POST"])
@app.route("/book", methods=["POST"])
def book_service():
    data = request.json
    print(f"DEBUG: Booking request data: {data}")
    try:
        user_id = session.get('user_id')
        if not user_id:
             print("DEBUG: Booking failed: No user_id in session")
             return jsonify({"success": False, "message": "Please login to book"}), 401

        customer_name = data.get('name') or session.get('user_name')
        email = data.get('email')
        phone = data.get('phone')
        vehicle_type = data.get('vehicle') or data.get('vehicleType')
        vehicle_number = data.get('vehicleNumber', '')
        service_package = data.get('package')
        date = data.get('date')
        time_val = data.get('time')
        addons = data.get('addons', [])
        addons_str = ", ".join(addons) if isinstance(addons, list) else str(addons)
        
        # Pickup Info
        location = data.get('location')
        is_pickup = data.get('is_pickup', 0)

        if not date or not time_val:
            return jsonify({"success": False, "message": "Date and time are required"}), 400

        conn = get_db()
        cursor = conn.cursor()

        query = """
        INSERT INTO bookings 
        (user_id, customer_name, email, phone, vehicle_type, vehicle_number, service_package, appointment_date, appointment_time, booking_date, booking_time, addons, location, is_pickup)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        cursor.execute(query, (
            user_id, customer_name, email, phone, vehicle_type, vehicle_number, service_package, 
            date, time_val, date, time_val, addons_str, location, is_pickup
        ))
        booking_id = cursor.fetchone()['id']

        print(f"DEBUG: Booking created successfully. ID: {booking_id}")
        
        # Notification
        msg = f"Booking Confirmed: {service_package} for {vehicle_type} on {date} at {time_val}."
        if is_pickup:
            msg = f"Pickup Requested: {service_package} for {vehicle_type} on {date} at {time_val}."
            
        cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, msg))

        conn.commit()
        cursor.close()
        conn.close()

        # Send Email Confirmation
        try:
            send_booking_email(customer_name, email, service_package, date, time_val, vehicle_number)
            
            # If pickup, send to staff too
            if is_pickup and location:
                try:
                    lat, lng = location.split(',')
                    login_phone = session.get('user_phone', 'N/A')
                    send_staff_pickup_email(customer_name, phone, login_phone, lat, lng)
                    print("DEBUG: Staff pickup email sent")
                except:
                    print("DEBUG: Failed to parse location or send staff email")

            print(f"DEBUG: Confirmation email sent to {email}")
        except Exception as mail_err:
            print(f"DEBUG: Mail ERROR: {mail_err}")

        return jsonify({
            "success": True, 
            "message": "Booking created successfully", 
            "bookingId": booking_id,
            "staffPhone": "8590624912" if is_pickup else None
        })
    except Exception as e:
        print(f"DEBUG: Booking ERROR: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/my_bookings/<int:user_id>")
@app.route("/my_bookings/<int:user_id>")
def my_bookings(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()

        query = """
        SELECT id, service_package as service_name, appointment_date as booking_date, appointment_time as booking_time, status
        FROM bookings
        WHERE user_id = %s
        ORDER BY appointment_date DESC, appointment_time DESC
        """

        cursor.execute(query, (user_id,))
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(bookings)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/pickup/request', methods=['POST'])
def request_pickup():
    data = request.json
    try:
        user_id = session.get('user_id')
        customer_name = session.get('user_name', 'Guest')
        login_phone = session.get('user_phone', 'N/A')
        
        lat = data.get('lat')
        lng = data.get('lng')
        # Use session phone/name or provided ones
        contact_phone = data.get('phone') or login_phone
        contact_name = session.get('user_name') or "Guest"

        if not contact_phone or contact_phone == 'N/A':
             # If no phone, we can't really book effectively?
             pass 
             
        location_str = f"{lat},{lng}"
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Create a booking entry marked as pickup
        query = """
        INSERT INTO bookings (user_id, customer_name, phone, location, is_pickup, status, service_package)
        VALUES (%s, %s, %s, %s, 1, 'Pending', 'Pickup Service')
        RETURNING id
        """
        cursor.execute(query, (user_id, customer_name, contact_phone, location_str))
        booking_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        # Send Email to Staff
        try:
            send_staff_pickup_email(customer_name, contact_phone, login_phone, lat, lng)
        except Exception as e:
            print(f"Error sending staff email: {e}")
            
        return jsonify({"success": True, "bookingId": booking_id, "staffPhone": "8590624912"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/pickup/status/<int:booking_id>', methods=['GET'])
def get_pickup_status(booking_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM bookings WHERE id = %s", (booking_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify(row) if row else jsonify({"status": "Not Found"}), 404
        # Verify user matches booking? Not strictly necessary for status check but good for privacy
        return jsonify(row) if row else jsonify({"status": "Not Found"}), 404
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 10", (user_id,))
        notifs = cursor.fetchall()
        return jsonify(serialize_db_rows(notifs))
    except Exception as e:
        return jsonify([])
    finally:
        cursor.close()
        conn.close()

# =========================
# UTILITY API ROUTES
# =========================

@app.route('/api/slots', methods=['GET'])
def get_slots():
    start = request.args.get('start')
    end = request.args.get('end')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if start and end:
            query = "SELECT appointment_date as date, appointment_time as time, vehicle_number FROM bookings WHERE appointment_date BETWEEN %s AND %s"
            cursor.execute(query, (start, end))
        else:
            query = "SELECT appointment_date as date, appointment_time as time, vehicle_number FROM bookings"
            cursor.execute(query)
            
        rows = cursor.fetchall()
        
        # Convert date and time objects to strings for JSON
        for row in rows:
            if row['date']:
                row['date'] = str(row['date'])
            if row['time']:
                # Convert timedelta or time object to HH:MM string
                t = row['time']
                if hasattr(t, 'total_seconds'): # timedelta
                    hours = int(t.total_seconds() // 3600)
                    minutes = int((t.total_seconds() % 3600) // 60)
                    row['time'] = f"{hours:02d}:{minutes:02d}"
                else:
                    row['time'] = t.strftime('%H:%M')
                    
        return jsonify(rows)
    except Exception as e:
        print(f"Error fetching slots: {e}")
        return jsonify([])
    finally:
        cursor.close()
        conn.close()

@app.route('/api/status', methods=['GET'])
def get_shop_status():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shop_status WHERE id = 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row:
        row['is_busy'] = bool(row['is_busy'])
        # Privacy check
        is_authenticated = ('user_id' in session) or (get_logged_in_user(request) is not None)
        if not is_authenticated and row['is_busy']:
            row['current_vehicle'] = "AUTH_REQUIRED"
        return jsonify(row)
    return jsonify({"is_busy": False, "message": "Ready"})

@app.route('/api/weather', methods=['GET'])
def get_weather():
    forecasts = [
        {"desc": "Sunny skies ahead—Perfect day for a wash!", "icon": "☀️"},
        {"desc": "Rain expected tomorrow—Book a rain-check wax today!", "icon": "🌧️"},
        {"desc": "Perfect weather for a ceramic coating!", "icon": "✨"}
    ]
    return jsonify(random.choice(forecasts))

@app.route('/api/loyalty/<phone>', methods=['GET'])
def get_loyalty(phone):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT stamps FROM users WHERE phone = %s", (phone,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    stamps = user['stamps'] if user else random.randint(0, 4)
    return jsonify({"stamps": stamps, "freeWash": stamps >= 5})

@app.route('/api/update-profile', methods=['POST'])
def update_user_profile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    phone = data.get('phone')
    email = data.get('email')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Check if email/phone already taken by another user
        cursor.execute("SELECT id FROM users WHERE (email = %s OR phone = %s) AND id != %s", (email, phone, session['user_id']))
        if cursor.fetchone():
             return jsonify({"success": False, "message": "Email or Phone already exists"}), 400

        cursor.execute("UPDATE users SET phone = %s, email = %s WHERE id = %s", (phone, email, session['user_id']))
        conn.commit()
        
        session['user_phone'] = phone
        session['user_email'] = email
        
        return jsonify({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/upload-profile-pic', methods=['POST'])
def upload_profile_pic():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
        
    if file:
        filename = f"user_{session['user_id']}_{int(time.time())}.png"
        upload_folder = os.path.join(app.static_folder, 'uploads', 'profiles')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Save to DB
        relative_path = f"/uploads/profiles/{filename}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET profile_pic = %s WHERE id = %s", (relative_path, session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "profile_pic": relative_path})
    
    return jsonify({"success": False, "message": "Upload failed"}), 400


@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    if 'user_id' not in session:
        return jsonify({"success": False}), 401
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})

# =========================
# OTHER USER REQUESTED ROUTES
# =========================

@app.route("/api/add_vehicle", methods=["POST"])
@app.route("/add_vehicle", methods=["POST"])
def add_vehicle():
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        query = "INSERT INTO vehicles (user_id, vehicle_number, vehicle_type, model) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (data["user_id"], data["vehicle_number"], data["vehicle_type"], data["model"]))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Vehicle added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/update_profile", methods=["PUT"])
@app.route("/update_profile", methods=["PUT"])
def update_profile():
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        query = "UPDATE users SET fullname=%s, phone=%s WHERE id=%s"
        cursor.execute(query, (data["fullname"], data["phone"], data["id"]))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Profile updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/pay", methods=["POST"])
@app.route("/pay", methods=["POST"])
def make_payment():
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        query = "INSERT INTO payments (booking_id, amount, payment_method, payment_status) VALUES (%s, %s, %s, 'paid')"
        cursor.execute(query, (data["booking_id"], data["amount"], data["method"]))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Payment successful"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# =========================
# GAMING-INSPIRED FEATURES API
# =========================

@app.route('/api/packages', methods=['GET'])
def get_packages():
    """Get all active service packages"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM packages WHERE is_active = 1 ORDER BY price ASC")
        packages = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(packages))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/addons', methods=['GET'])
def get_addons():
    """Get all active add-ons"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM addons WHERE is_active = 1 ORDER BY price ASC")
        addons = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(addons))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/subscribe', methods=['POST'])
def create_subscription():
    """Create a new subscription for Unlimited Club"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    data = request.json
    user_id = session['user_id']
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if user already has an active subscription
        cursor.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = %s AND status = 'active' AND end_date >= CURRENT_DATE
        """, (user_id,))
        
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "You already have an active subscription"}), 400
        
        # Create new subscription (30 days from now)
        cursor.execute("""
            INSERT INTO subscriptions (user_id, plan_name, price, start_date, end_date, status)
            VALUES (%s, 'Unlimited Club', 999.00, CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', 'active')
            RETURNING id
        """, (user_id,))
        
        conn.commit()
        subscription_id = cursor.fetchone()['id']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Subscription activated successfully!",
            "subscription_id": subscription_id
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/subscription/status', methods=['GET'])
def get_subscription_status():
    """Get user's subscription status"""
    if 'user_id' not in session:
        return jsonify({"subscribed": False})
    
    user_id = session['user_id']
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = %s AND status = 'active' AND end_date >= CURRENT_DATE
            ORDER BY end_date DESC LIMIT 1
        """, (user_id,))
        
        subscription = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if subscription:
            return jsonify({
                "subscribed": True,
                "subscription": serialize_db_row(subscription)
            })
        else:
            return jsonify({"subscribed": False})
    except Exception as e:
        return jsonify({"subscribed": False, "error": str(e)})

@app.route('/api/loyalty/status', methods=['GET'])
def get_loyalty_status():
    """Get user's loyalty points status"""
    if 'user_id' not in session:
        return jsonify({"points": 0, "total_washes": 0, "free_washes": 0})
    
    user_id = session['user_id']
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get or create loyalty record
        cursor.execute("SELECT * FROM loyalty_points WHERE user_id = %s", (user_id,))
        loyalty = cursor.fetchone()
        
        if not loyalty:
            cursor.execute("""
                INSERT INTO loyalty_points (user_id, total_washes, free_washes, points)
                VALUES (%s, 0, 0, 0)
            """, (user_id,))
            conn.commit()
            loyalty = {"total_washes": 0, "free_washes": 0, "points": 0}
        
        cursor.close()
        conn.close()
        
        return jsonify(serialize_db_row(loyalty) if loyalty else {"total_washes": 0, "free_washes": 0, "points": 0})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/loyalty/update', methods=['POST'])
def update_loyalty():
    """Update loyalty points after completed wash"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    user_id = session['user_id']
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get current loyalty
        cursor.execute("SELECT * FROM loyalty_points WHERE user_id = %s", (user_id,))
        loyalty = cursor.fetchone()
        
        if not loyalty:
            cursor.execute("""
                INSERT INTO loyalty_points (user_id, total_washes, free_washes, points, last_wash_date)
                VALUES (%s, 1, 0, 10, CURRENT_DATE)
            """, (user_id,))
        else:
            total_washes = loyalty['total_washes'] + 1
            free_washes = loyalty['free_washes']
            points = loyalty['points'] + 10
            
            # Every 5 washes = 1 free wash
            if total_washes % 5 == 0:
                free_washes += 1
            
            cursor.execute("""
                UPDATE loyalty_points 
                SET total_washes = %s, free_washes = %s, points = %s, last_wash_date = CURRENT_DATE
                WHERE user_id = %s
            """, (total_washes, free_washes, points, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "Loyalty updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/stations', methods=['GET'])
def get_stations():
    """Get all stations with their current status"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, b.customer_name, b.vehicle_number, b.service_package
            FROM stations s
            LEFT JOIN bookings b ON s.current_booking_id = b.id
            ORDER BY s.id ASC
        """)
        stations = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(stations))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/stations/<int:station_id>/update', methods=['POST'])
def update_station_status(station_id):
    """Update station status (admin/staff only)"""
    role = session.get('role')
    if role not in ['admin', 'staff']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    status = data.get('status', 'free')
    current_vehicle = data.get('current_vehicle')
    booking_id = data.get('booking_id')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE stations 
            SET status = %s, current_vehicle = %s, current_booking_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (status, current_vehicle, booking_id, station_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Station updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit customer feedback"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    data = request.json
    user_id = session['user_id']
    booking_id = data.get('booking_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    if not rating or rating < 1 or rating > 5:
        return jsonify({"success": False, "message": "Invalid rating"}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feedback (user_id, booking_id, rating, comment)
            VALUES (%s, %s, %s, %s)
        """, (user_id, booking_id, rating, comment))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Thank you for your feedback!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



# =========================
# EMAIL HELPER
# =========================
def send_booking_email(name, to_email, package, date, time_val, vehicle_no):
    sender_email = os.getenv('MAIL_USER', 'thattilservicecentree@gmail.com')
    sender_password = os.getenv('MAIL_PASS', 'yxty obey rllu thyg')
    
    if not sender_email or not sender_password:
        print("DEBUG: Missing email credentials in .env")
        return

    msg = MIMEMultipart()
    msg['From'] = f"D2 CAR WASH <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = f"Booking Confirmation - D2 CAR WASH (#{random.randint(1000, 9999)})"

    body = f"""
    <h2>Booking Confirmed!</h2>
    <p>Dear <b>{name}</b>,</p>
    <p>Thank you for choosing D2 CAR WASH. Your appointment has been successfully scheduled.</p>
    <hr>
    <p><b>Vehicle:</b> {vehicle_no}</p>
    <p><b>Service Package:</b> {package}</p>
    <p><b>Date:</b> {date}</p>
    <p><b>Time:</b> {time_val}</p>
    <hr>
    <p>We'll see you there! Includes free coffee while you wait.</p>
    <p>Regards,<br><b>D2 CAR WASH Team</b><br>Thrissur, Kerala</p>
    """
    
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
    except Exception as e:
        raise e

def send_staff_pickup_email(customer_name, contact_phone, login_phone, lat, lng):
    sender_email = os.getenv('MAIL_USER', 'thattilservicecentree@gmail.com')
    sender_password = os.getenv('MAIL_PASS', 'yxty obey rllu thyg')
    staff_email = "delvindavis031@gmail.com"
    
    if not sender_email or not sender_password:
        return

    msg = MIMEMultipart()
    msg['From'] = f"D2 Pickup Alert <{sender_email}>"
    msg['To'] = staff_email
    msg['Subject'] = f"NEW PICKUP REQUEST: {customer_name}"

    maps_link = f"https://www.google.com/maps?q={lat},{lng}"

    body = f"""
    <h2>New Pickup Service Request</h2>
    <p><b>Customer:</b> {customer_name}</p>
    <p><b>Contact Phone:</b> {contact_phone}</p>
    <p><b>Login Phone:</b> {login_phone}</p>
    <p><b>Location:</b> <a href="{maps_link}">View on Google Maps</a> ({lat}, {lng})</p>
    <hr>
    <p>Please confirm this pickup in the admin portal.</p>
    """
    
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, staff_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"SMTP Error: {e}")

# =========================
# ADMINISTRATIVE ROUTES
# =========================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['admin', 'master']:
            if session.get('user_email') != "delvindavis031@gmail.com":
                return jsonify({"success": False, "message": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/admin/analytics', methods=['GET'])
@admin_required
def get_admin_analytics():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Revenue
        cursor.execute("SELECT SUM(total_price) as revenue FROM payments")
        rev_row = cursor.fetchone()
        revenue = rev_row['revenue'] if rev_row and rev_row['revenue'] else 0
        
        # Bookings count
        cursor.execute("SELECT COUNT(*) as count FROM bookings")
        total_bookings = cursor.fetchone()['count']
        
        # Users count
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        # Subscriptions
        cursor.execute("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'")
        active_subs = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "revenue": float(revenue),
            "total_bookings": total_bookings,
            "total_users": total_users,
            "active_subscriptions": active_subs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/bookings', methods=['GET'])
@admin_required
def get_admin_bookings():
    date = request.args.get('date')
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if date:
            cursor.execute("SELECT * FROM bookings WHERE appointment_date = %s ORDER BY appointment_time", (date,))
        else:
            cursor.execute("SELECT * FROM bookings ORDER BY appointment_date DESC, appointment_time DESC LIMIT 100")
        
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(bookings))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/booking/status', methods=['POST'])
@admin_required
def update_booking_status():
    data = request.json
    booking_id = data.get('id')
    new_status = data.get('status')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", (new_status, booking_id))
        conn.commit()
        
        # Create notification for user
        cursor.execute("SELECT user_id, customer_name, service_package FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()
        if booking and booking[0]:
            user_id = booking[0]
            msg = f"Your {booking[2]} status changed to: {new_status}"
            cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, msg))
            conn.commit()
            
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_admin_users():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, fullname, email, phone, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(users))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    init_db()
    port = int(os.getenv('PORT', 5000))
    print(f"Server running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
