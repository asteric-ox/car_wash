from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import secrets
import time
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import qrcode
import io
import base64
import datetime
from datetime import timedelta
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
def get_db_params():
    return {
        "host": os.getenv('MYSQLHOST', os.getenv('DB_HOST', 'localhost')),
        "user": os.getenv('MYSQLUSER', os.getenv('DB_USER', 'root')),
        "password": os.getenv('MYSQLPASSWORD', os.getenv('DB_PASS', 'Delvin@2005')),
        "database": os.getenv('MYSQLDATABASE', os.getenv('DB_NAME', 'car_wash')),
        "port": int(os.getenv('MYSQLPORT', 3306))
    }

def get_db():
    params = get_db_params()
    # Do not print password for security
    print(f"DEBUG: Connecting to {params['user']}@{params['host']}:{params['port']}/{params['database']}")
    return mysql.connector.connect(
        host=params['host'],
        user=params['user'],
        password=params['password'],
        database=params['database'],
        port=params['port'],
        connection_timeout=10,
        buffered=True
    )

def init_db():
    try:
        params = get_db_params()
        
        # Step 1: Connect WITHOUT database name to create it if missing (Fix Method 1)
        print(f"DEBUG: Checking if database {params['database']} exists...")
        temp_conn = mysql.connector.connect(
            host=params['host'],
            user=params['user'],
            password=params['password'],
            port=params['port']
        )
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {params['database']}")
        temp_cursor.close()
        temp_conn.close()
        print(f"Database {params['database']} initialized successfully")

        # Step 2: Connect TO the database and create tables
        conn = get_db()
        cursor = conn.cursor()

        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fullname VARCHAR(255),
            name VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            phone VARCHAR(50) UNIQUE,
            password VARCHAR(255),
            password_hash VARCHAR(255),
            role ENUM('admin','staff','customer') DEFAULT 'customer',
            status ENUM('active','inactive') DEFAULT 'active',
            stamps INT DEFAULT 0,
            reset_otp VARCHAR(6),
            otp_expiry DATETIME,
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

        # Bookings Table (Updated status for VARCHAR)
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
            booking_date DATE,
            booking_time TIME,
            addons TEXT,
            location VARCHAR(255),
            is_pickup BOOLEAN DEFAULT 0,
            status VARCHAR(50) DEFAULT 'Pending',
            assigned_staff INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_staff) REFERENCES users(id)
        )
        """)

        # Admins, Notifications, Staff, etc. (Other tables)
        cursor.execute("CREATE TABLE IF NOT EXISTS admins (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(255) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL, role VARCHAR(50) DEFAULT 'staff', token VARCHAR(255) NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS shop_status (id INT PRIMARY KEY, status VARCHAR(50) DEFAULT 'OPEN', message VARCHAR(255), is_busy BOOLEAN DEFAULT 0, current_vehicle VARCHAR(255), pickup_active BOOLEAN DEFAULT 1, queue_count INT DEFAULT 0, wait_time INT DEFAULT 0, updated_by VARCHAR(255), updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)")
        
        # Seed default data if empty
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            services_data = [('Basic Wash', 200.00), ('Normal', 350.00), ('Super', 450.00), ('Premium', 600.00), ('Premium Plus', 800.00)]
            cursor.executemany("INSERT INTO services (service_name, price) VALUES (%s, %s)", services_data)

        cursor.execute("SELECT COUNT(*) FROM shop_status")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO shop_status (id, status, message) VALUES (1, 'OPEN', 'Ready to Shine!')")

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
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE token = %s", (token,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            # Check if it's a mobile/API admin with token
            mobile_admin = get_logged_in_user(request)
            if not mobile_admin:
                return jsonify({"success": False, "message": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

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
        cursor = conn.cursor(dictionary=True)
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
    except mysql.connector.IntegrityError as e:
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
        cursor = conn.cursor(dictionary=True)

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
        """

        cursor.execute(query, (
            user_id, customer_name, email, phone, vehicle_type, vehicle_number, service_package, 
            date, time_val, date, time_val, addons_str, location, is_pickup
        ))
        booking_id = cursor.lastrowid

        print(f"DEBUG: Booking created successfully. ID: {booking_id}")
        
        conn.commit()
        cursor.close()
        conn.close()

        # Send Notifications (Email & SMS)
        try:
            # Email
            if not is_pickup:
                send_booking_email(booking_id, customer_name, email, service_package, date, time_val, vehicle_number)
                print(f"DEBUG: Confirmation email sent to {email}")
            
            # SMS (New Feature)
            sms_text = f"D2 Car Wash: Booking Confirmed! ID: #{booking_id}. {service_package} on {date} at {time_val}. Thank you!"
            if is_pickup:
                sms_text = f"D2 Car Wash: Pickup Request Received! ID: #{booking_id}. Our staff will contact you shortly. Ph: 8590624912"
            
            send_sms_notification(phone, sms_text)

            # If pickup, send alert to staff ONLY (Customer gets QR later when approved)
            if is_pickup and location:
                try:
                    lat, lng = location.split(',')
                    login_phone = session.get('user_phone', 'N/A')
                    send_staff_pickup_email(customer_name, phone, login_phone, lat, lng)
                    print("DEBUG: Staff pickup email sent")
                except:
                    print("DEBUG: Failed to parse location or send staff email")

        except Exception as notify_err:
            print(f"DEBUG: Notification helper error: {notify_err}")

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
        cursor = conn.cursor(dictionary=True)

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
        """
        cursor.execute(query, (user_id, customer_name, contact_phone, location_str))
        booking_id = cursor.lastrowid
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

@app.route('/api/admin/pickup/pending', methods=['GET'])
@admin_required
def get_pending_pickups():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.id, b.customer_name, b.phone, b.location, b.status, b.created_at
            FROM bookings b
            WHERE b.is_pickup = 1
            ORDER BY b.created_at DESC
            LIMIT 50
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(rows))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/pickup/approve/<int:booking_id>', methods=['POST'])
@admin_required
def approve_pickup(booking_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings WHERE id = %s AND is_pickup = 1", (booking_id,))
        booking = cursor.fetchone()
        if not booking:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Pickup booking not found"}), 404

        cursor.execute("UPDATE bookings SET status = 'Confirmed' WHERE id = %s", (booking_id,))
        # notify user
        if booking.get('user_id'):
            cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                           (booking['user_id'], "Your pickup request has been confirmed! Staff will arrive shortly."))
        conn.commit()
        cursor.close()
        conn.close()

        # Send both Staff notification and Customer QR Email
        send_pickup_confirmation_emails(booking)

        return jsonify({"success": True, "message": f"Pickup approved. Phone sent to staff and QR sent to customer."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def send_pickup_confirmation_emails(booking):
    """Helper to send the pickup confirmed emails to both staff and customer."""
    try:
        booking_id = booking['id']
        sender_email = os.getenv('MAIL_USER', 'thattilservicecentree@gmail.com')
        sender_password = os.getenv('MAIL_PASS', 'jycr hgbu cyjp bfst')
        staff_email = "delvindavis031@gmail.com"
        lat_lng = booking.get('location', 'N/A')
        maps_link = f"https://www.google.com/maps?q={lat_lng}" if ',' in str(lat_lng) else '#'

        # --- Generate QR code for pickup verification ---
        qr_data = f"PICKUP-{booking_id}"
        qr_img = qrcode.make(qr_data)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_bytes = qr_buffer.getvalue()

        # --- Staff email with phone + maps ---
        staff_msg = MIMEMultipart()
        staff_msg['From'] = f"D2 Admin <{sender_email}>"
        staff_msg['To'] = staff_email
        staff_msg['Subject'] = f"✅ PICKUP CONFIRMED - {booking['customer_name']}"
        staff_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;border:1px solid #eee;border-radius:10px;">
            <h2 style="color:#06b6d4;">Pickup Confirmed</h2>
            <p><b>Customer:</b> {booking['customer_name']}</p>
            <p><b>Phone:</b> <a href="tel:{booking['phone']}" style="color:#06b6d4;font-size:20px;font-weight:bold;">{booking['phone']}</a></p>
            <p><b>Location:</b> <a href="{maps_link}">View on Maps</a></p>
            <p><b>Booking ID:</b> #{booking_id}</p>
            <hr>
            <p>Please call the customer and proceed to their location.</p>
        </div>"""
        staff_msg.attach(MIMEText(staff_body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, staff_email, staff_msg.as_string())
        server.quit()

        # --- Customer email with QR code ---
        customer_email = booking.get('email')
        if customer_email:
            cust_msg = MIMEMultipart('related')
            cust_msg['From'] = f"D2 Car Wash <{sender_email}>"
            cust_msg['To'] = customer_email
            cust_msg['Subject'] = f"🚗 Your Pickup is Confirmed! - D2 Car Wash"

            cust_html = f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;border:1px solid #eee;border-radius:12px;">
                <h2 style="color:#06b6d4;text-align:center;">✅ Pickup Confirmed!</h2>
                <p>Dear <b>{booking['customer_name']}</b>,</p>
                <p>Your pickup request has been <b style="color:#06b6d4;">confirmed</b>. Our staff will arrive at your location shortly.</p>
                <p><b>Pickup ID:</b> #{str(booking_id).zfill(4)}</p>
                <div style="text-align:center;margin:24px 0;">
                    <p style="color:#555;">Show this QR code to our staff when they arrive:</p>
                    <img src="cid:pickup_qr" alt="Pickup QR Code" style="width:180px;height:180px;border:4px solid #06b6d4;border-radius:12px;padding:8px;">
                </div>
                <p style="color:#888;font-size:12px;text-align:center;">Booking Reference: PICKUP-{booking_id}</p>
                <hr style="border:0;border-top:1px solid #eee;margin:16px 0;">
                <p>Regards,<br><b>D2 Car Wash Team</b><br>Thrissur, Kerala</p>
            </div>"""

            cust_msg.attach(MIMEText(cust_html, 'html'))
            qr_attachment = MIMEImage(qr_bytes, name='pickup_qr.png')
            qr_attachment.add_header('Content-ID', '<pickup_qr>')
            qr_attachment.add_header('Content-Disposition', 'inline', filename='pickup_qr.png')
            cust_msg.attach(qr_attachment)

            server2 = smtplib.SMTP('smtp.gmail.com', 587)
            server2.starttls()
            server2.login(sender_email, sender_password)
            server2.sendmail(sender_email, customer_email, cust_msg.as_string())
            server2.quit()
    except Exception as e:
        print(f"Error in send_pickup_confirmation_emails: {e}")

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/admin/pickup/update/<int:booking_id>', methods=['POST'])
@admin_required
def update_pickup_status(booking_id):
    """Update pickup status to any value and notify the customer."""
    data = request.json
    new_status = data.get('status', '').strip()

    VALID_STATUSES = ['Pending', 'Confirmed', 'Picked', 'Washing', 'Drying', 'Delivered', 'Cancelled']
    if new_status not in VALID_STATUSES:
        return jsonify({"success": False, "message": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings WHERE id = %s AND is_pickup = 1", (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Pickup booking not found"}), 404

        cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", (new_status, booking_id))

        # Customer notification messages per status
        notif_messages = {
            'Confirmed':  "✅ Your pickup has been confirmed! Staff will arrive shortly.",
            'Picked':     "🚗 Staff has picked up your vehicle and is on the way.",
            'Washing':    "🫧 Your vehicle is now being washed.",
            'Drying':     "💨 Your vehicle is being dried and polished.",
            'Delivered':  "🎉 Your vehicle has been delivered. Thank you for choosing D2 Car Wash!",
            'Cancelled':  "❌ Your pickup request has been cancelled. Please contact us for more info.",
        }
        if booking.get('user_id') and new_status in notif_messages:
            cursor.execute(
                "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                (booking['user_id'], notif_messages[new_status])
            )

        conn.commit()
        cursor.close()
        conn.close()

        # If confirming, send staff email AND customer QR code email
        if new_status == 'Confirmed':
            send_pickup_confirmation_emails(booking)

        return jsonify({"success": True, "message": f"Pickup #{booking_id} status updated to '{new_status}'.", "status": new_status})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500





@app.route('/api/pickup/status/<int:booking_id>', methods=['GET'])
def get_pickup_status(booking_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if booking:
            return jsonify({"success": True, "status": booking['status']})
        return jsonify({"success": False, "message": "Booking not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
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
    cursor = conn.cursor(dictionary=True)
    
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
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM shop_status WHERE id = 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            # Conversion for JSON
            row['is_busy'] = bool(row['is_busy'])
            row['pickup_active'] = bool(row['pickup_active'])
            
            # Privacy for non-authenticated users
            is_authenticated = ('user_id' in session) or (get_logged_in_user(request) is not None)
            if not is_authenticated and row['is_busy']:
                row['current_vehicle'] = "AUTH_REQUIRED"
            
            return jsonify(serialize_db_row(row))
        return jsonify({"status": "OPEN", "message": "Ready to Shine!", "is_busy": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/status', methods=['POST'])
@admin_required
def update_shop_status():
    data = request.json
    status = data.get('status', 'OPEN')
    message = data.get('message', '')
    is_busy = data.get('is_busy', False)
    current_vehicle = data.get('current_vehicle', '')
    pickup_active = data.get('pickup_active', True)
    queue_count = data.get('queue_count', 0)
    wait_time = data.get('wait_time', 0)
    updated_by = session.get('user_name', 'Admin')

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE shop_status 
            SET status=%s, message=%s, is_busy=%s, current_vehicle=%s, 
                pickup_active=%s, queue_count=%s, wait_time=%s, updated_by=%s
            WHERE id = 1
        """, (status, message, is_busy, current_vehicle, pickup_active, queue_count, wait_time, updated_by))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "success": True, 
            "message": "Shop Status Updated Successfully",
            "status": status
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/register-staff', methods=['POST'])
@admin_required
def register_staff():
    data = request.json
    fullname = data.get('fullname')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')

    if not all([fullname, email, password]):
        return jsonify({"success": False, "message": "Required fields missing"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        hashed_pw = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (fullname, email, phone, password, password_hash, role)
            VALUES (%s, %s, %s, %s, %s, 'staff')
        """, (fullname, email, phone, hashed_pw, hashed_pw))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Staff {fullname} registered successfully"})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "Email or Phone already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

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
    cursor = conn.cursor(dictionary=True)
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
        cursor = conn.cursor(dictionary=True)
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
        cursor = conn.cursor(dictionary=True)
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
        cursor = conn.cursor(dictionary=True)
        
        # Check if user already has an active subscription
        cursor.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = %s AND status = 'active' AND end_date >= CURDATE()
        """, (user_id,))
        
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "You already have an active subscription"}), 400
        
        # Create new subscription (30 days from now)
        cursor.execute("""
            INSERT INTO subscriptions (user_id, plan_name, price, start_date, end_date, status)
            VALUES (%s, 'Unlimited Club', 999.00, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'active')
        """, (user_id,))
        
        conn.commit()
        subscription_id = cursor.lastrowid
        
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
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = %s AND status = 'active' AND end_date >= CURDATE()
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
        cursor = conn.cursor(dictionary=True)
        
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
        cursor = conn.cursor(dictionary=True)
        
        # Get current loyalty
        cursor.execute("SELECT * FROM loyalty_points WHERE user_id = %s", (user_id,))
        loyalty = cursor.fetchone()
        
        if not loyalty:
            cursor.execute("""
                INSERT INTO loyalty_points (user_id, total_washes, free_washes, points, last_wash_date)
                VALUES (%s, 1, 0, 10, CURDATE())
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
                SET total_washes = %s, free_washes = %s, points = %s, last_wash_date = CURDATE()
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
        cursor = conn.cursor(dictionary=True)
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
def send_sms_notification(phone, message):
    """
    Utility to send SMS. Supports Twilio, MSG91 or custom Gateway.
    Currently logs to console and database for preview.
    """
    print(f"\n[SMS SENT TO {phone}]: {message}\n")
    # You can integrate Twilio here:
    # client = Client(account_sid, auth_token)
    # client.messages.create(body=message, from_=twilio_num, to=phone)
    return True

def send_booking_email(booking_id, name, to_email, package, date, time_val, vehicle_no):
    sender_email = os.getenv('MAIL_USER', 'thattilservicecentree@gmail.com')
    sender_password = os.getenv('MAIL_PASS', 'jycr hgbu cyjp bfst')
    
    if not sender_email or not sender_password:
        print("DEBUG: Missing email credentials in .env")
        return

    msg = MIMEMultipart('related')
    msg['From'] = f"D2 CAR WASH <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = f"Booking Confirmation - D2 CAR WASH (#{booking_id})"

    # Generate QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(str(booking_id))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    qr_bytes = img_byte_arr.getvalue()

    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #06b6d4; text-align: center;">Booking Confirmed!</h2>
        <p>Dear <b>{name}</b>,</p>
        <p>Thank you for choosing D2 CAR WASH. Your appointment has been successfully scheduled.</p>
        <hr style="border: 0; border-top: 1px solid #eee;">
        <p><b>Booking ID:</b> #{booking_id}</p>
        <p><b>Vehicle:</b> {vehicle_no}</p>
        <p><b>Service Package:</b> {package}</p>
        <p><b>Date:</b> {date}</p>
        <p><b>Time:</b> {time_val}</p>
        <hr style="border: 0; border-top: 1px solid #eee;">
        
        <div style="text-align: center; margin: 20px 0;">
            <p style="font-size: 14px; color: #666;">Scan this QR code at the station for verification:</p>
            <img src="cid:qrcode" style="width: 200px; height: 200px;">
        </div>

        <p>We'll see you there! Includes free coffee while you wait.</p>
        <p>Regards,<br><b>D2 CAR WASH Team</b><br>Thrissur, Kerala</p>
    </div>
    """
    
    msg.attach(MIMEText(body, 'html'))

    # Attach QR Code Image
    img_qr = MIMEImage(qr_bytes)
    img_qr.add_header('Content-ID', '<qrcode>')
    msg.attach(img_qr)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
    except Exception as e:
        print(f"DEBUG: Email sending error: {e}")

def send_otp_email(to_email, otp):
    sender_email = os.getenv('MAIL_USER', 'thattilservicecentree@gmail.com')
    sender_password = os.getenv('MAIL_PASS', 'jycr hgbu cyjp bfst')
    
    if not sender_email or not sender_password:
        return

    msg = MIMEMultipart('related')
    msg['From'] = f"D2 CAR WASH <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = f"🔐 Your Password Reset OTP - D2 CAR WASH"

    body = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; padding: 40px; color: #ffffff;">
        <div style="max-width: 600px; margin: 0 auto; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; padding: 40px; text-align: center; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
            <div style="margin-bottom: 30px;">
                <h1 style="color: #06b6d4; font-size: 28px; font-weight: 800; margin: 0; letter-spacing: -1px;">D2 CAR WASH</h1>
                <p style="color: #64748b; font-size: 14px; margin-top: 5px; text-transform: uppercase; letter-spacing: 2px;">Premium Auto Detailing</p>
            </div>
            
            <div style="margin-bottom: 30px;">
                <h2 style="font-size: 24px; margin-bottom: 10px;">Reset Your Password</h2>
                <p style="color: #94a3b8; line-height: 1.6;">We received a request to reset your password. Use the verification code below to proceed.</p>
            </div>
            
            <div style="background: rgba(6, 182, 212, 0.1); border: 2px dashed #06b6d4; border-radius: 16px; padding: 20px; margin-bottom: 30px;">
                <span style="font-size: 42px; font-weight: 900; color: #06b6d4; letter-spacing: 8px;">{otp}</span>
            </div>
            
            <p style="color: #64748b; font-size: 13px; margin-bottom: 30px;">This code will expire in 10 minutes for your security.</p>
            
            <div style="border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 30px;">
                <p style="color: #475569; font-size: 12px; line-height: 1.5;">If you didn't request this code, you can safely ignore this email. Someone might have typed your email address by mistake.</p>
            </div>
            
            <div style="margin-top: 40px; font-size: 14px; font-weight: 600;">
                <p style="color: #06b6d4; margin: 0;">D2 CAR WASH Team</p>
                <p style="color: #475569; margin: 5px 0 0 0;">Thrissur, Kerala</p>
            </div>
        </div>
    </div>
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
        print(f"DEBUG: Failed to send OTP email: {e}")

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        # For security, don't confirm if email exists or not
        return jsonify({"success": True, "message": "If an account exists with this email, an OTP has been sent."})

    otp = str(random.randint(100000, 999999))
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)

    cursor.execute("UPDATE users SET reset_otp = %s, otp_expiry = %s WHERE id = %s", (otp, expiry, user['id']))
    conn.commit()
    cursor.close()
    conn.close()

    send_otp_email(email, otp)
    return jsonify({"success": True, "message": "If an account exists with this email, an OTP has been sent."})

@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("password")

    if not email or not otp or not new_password:
        return jsonify({"success": False, "message": "All fields are required"}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, otp_expiry FROM users WHERE email = %s AND reset_otp = %s", (email, otp))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Invalid OTP or email"}), 400

    # Check expiry
    if user['otp_expiry'] < datetime.datetime.now():
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "OTP has expired"}), 400

    hashed_pw = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password = %s, password_hash = %s, reset_otp = NULL, otp_expiry = NULL WHERE id = %s", 
                   (hashed_pw, hashed_pw, user['id']))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Password reset successful! Please login."})

def send_staff_pickup_email(customer_name, contact_phone, login_phone, lat, lng):
    sender_email = os.getenv('MAIL_USER', 'thattilservicecentree@gmail.com')
    sender_password = os.getenv('MAIL_PASS', 'jycr hgbu cyjp bfst')
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

@app.route('/api/admin/analytics', methods=['GET'])
@admin_required
def get_admin_analytics():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Revenue from payments
        try:
            cursor.execute("SELECT SUM(amount) as revenue FROM payments")
            rev_row = cursor.fetchone()
            revenue = rev_row['revenue'] if rev_row and rev_row['revenue'] else 0
        except:
            revenue = 0
        
        # Total Bookings count
        cursor.execute("SELECT COUNT(*) as count FROM bookings")
        total_bookings = cursor.fetchone()['count']
        
        # Total Users count
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        # Upcoming Appointments (Status Pending or Approved and date >= today)
        today = datetime.date.today().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) as count FROM bookings 
            WHERE (status = 'Pending' OR status = 'Approved') 
            AND appointment_date >= %s
        """, (today,))
        upcoming = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "revenue": float(revenue),
            "total_bookings": total_bookings,
            "total_users": total_users,
            "upcoming_appointments": upcoming
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/bookings/direct', methods=['POST'])
@admin_required
def add_direct_booking():
    """Manual entry for walk-in customers"""
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Insert booking
        today_date = datetime.date.today().strftime('%Y-%m-%d')
        now_time = datetime.datetime.now().strftime('%H:%M:%S')
        
        cursor.execute("""
            INSERT INTO bookings (customer_name, phone, vehicle_number, vehicle_type, service_package, 
                                 appointment_date, appointment_time, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Completed')
        """, (data['customer_name'], data['phone'], data['vehicle_number'], data['vehicle_type'], 
              data['service_package'], today_date, now_time))
        
        booking_id = cursor.lastrowid
        
        # Record Payment (Revenue)
        amount = float(data.get('amount', 0))
        cursor.execute("""
            INSERT INTO payments (booking_id, amount, payment_method)
            VALUES (%s, %s, 'Cash')
        """, (booking_id, amount))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "booking_id": booking_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/bookings', methods=['GET'])
@admin_required
def get_admin_bookings():
    date = request.args.get('date')
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
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
        cursor.execute("SELECT user_id, customer_name, service_package, vehicle_type FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()
        if booking and booking[0]:
            user_id = booking[0]
            msg = f"Your {booking[2]} status changed to: {new_status}"
            cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, msg))
            conn.commit()

        # Check if we should add revenue (If status becomes 'Approved' or 'Confirmed')
        if new_status in ['Approved', 'Confirmed', 'Completed']:
            # Avoid duplicate payments for same booking
            cursor.execute("SELECT COUNT(*) FROM payments WHERE booking_id = %s", (booking_id,))
            if cursor.fetchone()[0] == 0:
                # Lookup price from services
                pkg = booking[2] if booking else ""
                cursor.execute("SELECT price FROM services WHERE service_name = %s", (pkg,))
                price_row = cursor.fetchone()
                # Default prices if not in DB
                defaults = {"Basic Wash": 200, "Normal": 350, "Super": 450, "Premium": 600, "Premium Plus": 800}
                amount = price_row[0] if price_row else defaults.get(pkg, 0)
                
                cursor.execute("INSERT INTO payments (booking_id, amount, payment_method) VALUES (%s, %s, 'Store')", 
                               (booking_id, amount))
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
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, fullname, email, phone, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(users))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/staff', methods=['GET'])
@admin_required
def get_admin_staff():
    """Get all staff members"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, fullname, email, phone, created_at FROM users WHERE role = 'staff' ORDER BY created_at DESC")
        staff = cursor.fetchall()
        
        # Get today's attendance status for each
        today = datetime.date.today().strftime('%Y-%m-%d')
        for s in staff:
            cursor.execute("SELECT status FROM staff_attendance WHERE staff_id = %s AND date = %s", (s['id'], today))
            attr = cursor.fetchone()
            s['today_status'] = attr['status'] if attr else 'Not Marked'
            
        cursor.close()
        conn.close()
        return jsonify(serialize_db_rows(staff))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/staff/<int:staff_id>', methods=['GET'])
@admin_required
def get_staff_details(staff_id):
    """Get full details of a staff member"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, fullname, email, phone, role, created_at FROM users WHERE id = %s", (staff_id,))
        staff = cursor.fetchone()
        
        if not staff:
            return jsonify({"success": False, "message": "Staff not found"}), 404
            
        # Get attendance history
        cursor.execute("SELECT date, status, notes FROM staff_attendance WHERE staff_id = %s ORDER BY date DESC LIMIT 30", (staff_id,))
        attendance = cursor.fetchall()
        staff['attendance_history'] = serialize_db_rows(attendance)
        
        # Get assigned bookings
        cursor.execute("SELECT id, customer_name, vehicle_number, status, appointment_date FROM bookings WHERE assigned_staff = %s ORDER BY appointment_date DESC LIMIT 10", (staff_id,))
        bookings = cursor.fetchall()
        staff['recent_jobs'] = serialize_db_rows(bookings)
        
        cursor.close()
        conn.close()
        return jsonify(serialize_db_row(staff))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/staff/attendance', methods=['POST'])
@admin_required
def mark_staff_attendance():
    """Mark attendance for staff"""
    data = request.json
    staff_id = data.get('staff_id')
    status = data.get('status') # Present or Absent
    notes = data.get('notes', '')
    date = datetime.date.today().strftime('%Y-%m-%d')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if already marked
        cursor.execute("SELECT id FROM staff_attendance WHERE staff_id = %s AND date = %s", (staff_id, date))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE staff_attendance SET status = %s, notes = %s WHERE id = %s", (status, notes, existing[0]))
        else:
            cursor.execute("INSERT INTO staff_attendance (staff_id, date, status, notes) VALUES (%s, %s, %s, %s)", 
                           (staff_id, date, status, notes))
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Attendance updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/admin/scan-qr", methods=["POST"])
@admin_required
def scan_qr():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    file = request.files['file']
    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
        img = Image.open(file)
        decoded = decode(img)
        if not decoded:
            return jsonify({"success": False, "message": "No QR code found in image"}), 400
        
        booking_id = decoded[0].data.decode('utf-8')
        booking_id = booking_id.strip()
        return jsonify({"success": True, "booking_id": booking_id})
    except Exception as e:
        return jsonify({"success": False, "message": f"Scan failed: {str(e)}"}), 500


@app.route("/api/admin/verify-booking", methods=["POST"])
@admin_required
def verify_booking():
    data = request.json
    raw_id = str(data.get("id", "")).strip()
    if not raw_id:
        return jsonify({"success": False, "message": "Booking ID is required"}), 400

    # Detect pickup QR (encoded as PICKUP-{id})
    is_pickup_qr = raw_id.upper().startswith("PICKUP-")
    if is_pickup_qr:
        booking_id = raw_id.upper().replace("PICKUP-", "").strip()
    else:
        booking_id = raw_id

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if is_pickup_qr:
        # --- Pickup QR scan → set status to Picked (Verified) ---
        cursor.execute(
            "SELECT b.*, u.email as user_email, u.fullname as user_name "
            "FROM bookings b LEFT JOIN users u ON b.user_id = u.id "
            "WHERE b.id = %s AND b.is_pickup = 1",
            (booking_id,)
        )
        booking = cursor.fetchone()
        if not booking:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": f"Pickup booking #{booking_id} not found"}), 404

        # Set status to Picked after scanning the QR at customer location
        cursor.execute("UPDATE bookings SET status = 'Picked' WHERE id = %s", (booking_id,))
        if booking.get('user_id'):
            cursor.execute(
                "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                (booking['user_id'], "✅ Your vehicle has been Picked and Verified via QR scan! It's now being transported to our station.")
            )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "success": True,
            "message": f"Pickup #{str(booking_id).zfill(4)} QR verified! Status updated to 'Picked'.",
            "booking": serialize_db_row(booking)
        })
    else:
        # --- Regular booking QR scan → set status to Washing ---
        cursor.execute("""
            SELECT b.*, u.email as user_email, u.fullname as user_name 
            FROM bookings b 
            LEFT JOIN users u ON b.user_id = u.id 
            WHERE b.id = %s
        """, (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Booking not found"}), 404

        cursor.execute("UPDATE bookings SET status = 'Washing' WHERE id = %s", (booking_id,))

        try:
            if booking.get('user_email'):
                send_verified_email(booking['user_name'], booking['user_email'], booking.get('vehicle_number', 'N/A'))
        except Exception as e:
            print(f"DEBUG: Failed to send verified email: {e}")

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Verified! Vehicle {booking.get('vehicle_number', 'N/A')} is now being washed.",
            "booking": serialize_db_row(booking)
        })

def send_verified_email(name, to_email, vehicle_no):
    sender_email = os.getenv('MAIL_USER', 'thattilservicecentree@gmail.com')
    sender_password = os.getenv('MAIL_PASS', 'jycr hgbu cyjp bfst')
    
    if not sender_email or not sender_password:
        return

    msg = MIMEMultipart()
    msg['From'] = f"D2 CAR WASH <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = "Verified! Your Wash is Starting - D2 CAR WASH"

    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #06b6d4; text-align: center;">Verified & Confirmed!</h2>
        <p>Dear <b>{name}</b>,</p>
        <p>Your booking for vehicle <b>{vehicle_no}</b> has been verified by our admin.</p>
        <p style="color: #06b6d4; font-size: 18px; font-weight: bold; text-align: center;">Your vehicle is now being washed! Enjoy the wash.</p>
        <hr style="border: 0; border-top: 1px solid #eee;">
        <p>Regards,<br><b>D2 CAR WASH Team</b><br>Thrissur, Kerala</p>
    </div>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"DEBUG: Verified email error: {e}")
# =========================
# INITIALIZATION
# =========================
try:
    init_db()
except Exception as e:
    print(f"Startup Database Error: {e}")

if __name__ == "__main__":
    # Local run logic
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
