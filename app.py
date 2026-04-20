from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import secrets
import time
from datetime import timedelta, datetime
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
    client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/car_wash'))
    return client.get_database()

def init_db():
    try:
        db = get_db()
        
        # Seed data for services
        if db.services.count_documents({}) == 0:
            services_data = [
                {'service_name': 'Basic Wash', 'price': 200.00},
                {'service_name': 'Normal', 'price': 350.00},
                {'service_name': 'Super', 'price': 450.00},
                {'service_name': 'Premium', 'price': 600.00},
                {'service_name': 'Premium Plus', 'price': 800.00}
            ]
            db.services.insert_many(services_data)

        # Seed data for shop status
        if db.shop_status.count_documents({'id': 1}) == 0:
            db.shop_status.insert_one({'id': 1, 'is_busy': False, 'message': 'Ready to Shine!', 'updated_at': datetime.utcnow()})

        # Seed data for admin
        if db.admins.count_documents({'username': 'admin'}) == 0:
            db.admins.insert_one({'username': 'admin', 'password': '1234', 'role': 'master', 'created_at': datetime.utcnow()})

        print("MongoDB initialized successfully!")
    except Exception as e:
        print(f"Error initializing MongoDB: {e}")

# =========================
# UTILITIES
# =========================
ACTIVE_TOKENS = {}

def serialize_db_row(row):
    if row is None:
        return None
    # Convert MongoDB ObjectId to string
    if '_id' in row:
        row['_id'] = str(row['_id'])
    
    for key, value in row.items():
        if isinstance(value, (datetime, timedelta)):
            row[key] = str(value)
        elif isinstance(value, ObjectId):
            row[key] = str(value)
    return row

def serialize_db_rows(rows):
    return [serialize_db_row(row) for row in rows]

def get_logged_in_user(req):
    token = req.headers.get('X-Admin-Token')
    if not token:
        return None
    
    db = get_db()
    user = db.admins.find_one({"token": token})
    return serialize_db_row(user)

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
@app.route("/register", methods=["POST"]) 
def register():
    data = request.json
    try:
        fullname = data.get("fullname") or data.get("name") or "User"
        email = data.get("email")
        phone = data.get("phone")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required"}), 400

        db = get_db()
        # Check if email or phone already exists
        if db.users.find_one({"email": email}):
            return jsonify({"success": False, "message": "Email already registered."}), 400
        
        if phone and db.users.find_one({"phone": phone}):
            return jsonify({"success": False, "message": "Phone number already registered."}), 400

        hashed_pw = generate_password_hash(password)

        user_doc = {
            "fullname": fullname,
            "name": fullname,
            "email": email,
            "phone": phone,
            "password": hashed_pw,
            "role": 'customer',
            "status": 'active',
            "stamps": 0,
            "created_at": datetime.utcnow()
        }

        result = db.users.insert_one(user_doc)
        print(f"DEBUG: Successfully registered {email}")
        return jsonify({"success": True, "message": "User registered successfully"})
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
    try:
        identifier = data.get("email") or data.get("identifier")
        password = data.get("password")

        # PERMANENT ADMIN CHECK
        if identifier == "delvindavis031@gmail.com" and password == "Delvin@2005":
            session.permanent = True
            session["user_id"] = "0"
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
                "user_id": "0",
                "redirect": "/admin.html",
                "role": "admin"
            })

        db = get_db()
        user = db.users.find_one({"$or": [{"email": identifier}, {"phone": identifier}]})

        if user and check_password_hash(user["password"], password):
            session.permanent = True
            session["user_id"] = str(user["_id"])
            session["user_name"] = user.get("fullname") or user.get("name") or "User"
            session["user_phone"] = user.get("phone")
            session["user_email"] = user.get("email")
            session["role"] = user.get("role", "customer")
            
            redirect_url = "/index.html"
            if session["role"] in ["admin", "staff"]:
                redirect_url = "/admin.html" if session["role"] == "admin" else "/staff.html"
            
            return jsonify({
                "success": True, 
                "message": "Login successful", 
                "user": {
                    "name": session["user_name"], 
                    "phone": session["user_phone"], 
                    "email": session["user_email"],
                    "role": session["role"]
                },
                "user_id": session["user_id"],
                "redirect": redirect_url,
                "role": session["role"]
            })

        return jsonify({"success": False, "message": "Invalid credentials"}), 401
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
    try:
        user_id = session.get('user_id')
        if not user_id:
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
        location = data.get('location')
        is_pickup = data.get('is_pickup', 0)

        if not date or not time_val:
            return jsonify({"success": False, "message": "Date and time are required"}), 400

        db = get_db()
        booking_doc = {
            "user_id": user_id,
            "customer_name": customer_name,
            "email": email,
            "phone": phone,
            "vehicle_type": vehicle_type,
            "vehicle_number": vehicle_number,
            "service_package": service_package,
            "appointment_date": date,
            "appointment_time": time_val,
            "addons": addons_str,
            "location": location,
            "is_pickup": is_pickup,
            "status": 'Pending',
            "created_at": datetime.utcnow()
        }

        result = db.bookings.insert_one(booking_doc)
        booking_id = str(result.inserted_id)

        msg = f"Booking Confirmed: {service_package} for {vehicle_type} on {date} at {time_val}."
        if is_pickup:
            msg = f"Pickup Requested: {service_package} for {vehicle_type} on {date} at {time_val}."
            
        db.notifications.insert_one({"user_id": user_id, "message": msg, "is_read": False, "created_at": datetime.utcnow()})

        # Send Email Confirmation
        try:
            send_booking_email(customer_name, email, service_package, date, time_val, vehicle_number)
            if is_pickup and location:
                lat, lng = location.split(',')
                login_phone = session.get('user_phone', 'N/A')
                send_staff_pickup_email(customer_name, phone, login_phone, lat, lng)
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

@app.route("/api/my_bookings/<user_id>")
@app.route("/my_bookings/<user_id>")
def my_bookings(user_id):
    try:
        db = get_db()
        bookings = list(db.bookings.find({"user_id": user_id}).sort([("appointment_date", -1), ("appointment_time", -1)]))
        
        # Rename service_package to service_name for compatibility
        for b in bookings:
            b['service_name'] = b.get('service_package')
            b['booking_date'] = b.get('appointment_date')
            b['booking_time'] = b.get('appointment_time')

        return jsonify(serialize_db_rows(bookings))
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
        contact_phone = data.get('phone') or login_phone
        location_str = f"{lat},{lng}"
        
        db = get_db()
        booking_doc = {
            "user_id": user_id,
            "customer_name": customer_name,
            "phone": contact_phone,
            "location": location_str,
            "is_pickup": 1,
            "status": 'Pending',
            "service_package": 'Pickup Service',
            "created_at": datetime.utcnow()
        }
        result = db.bookings.insert_one(booking_doc)
        booking_id = str(result.inserted_id)
        
        try:
            send_staff_pickup_email(customer_name, contact_phone, login_phone, lat, lng)
        except Exception as e:
            print(f"Error sending staff email: {e}")
            
        return jsonify({"success": True, "bookingId": booking_id, "staffPhone": "8590624912"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/pickup/status/<booking_id>', methods=['GET'])
def get_pickup_status(booking_id):
    try:
        db = get_db()
        row = db.bookings.find_one({"_id": ObjectId(booking_id)})
        return jsonify(serialize_db_row(row)) if row else jsonify({"status": "Not Found"}), 404
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    db = get_db()
    try:
        notifs = list(db.notifications.find({"user_id": user_id}).sort("created_at", -1).limit(10))
        return jsonify(serialize_db_rows(notifs))
    except Exception as e:
        return jsonify([])

# =========================
# UTILITY API ROUTES
# =========================

@app.route('/api/slots', methods=['GET'])
def get_slots():
    start = request.args.get('start')
    end = request.args.get('end')
    
    db = get_db()
    try:
        query = {}
        if start and end:
            query["appointment_date"] = {"$gte": start, "$lte": end}
            
        bookings = list(db.bookings.find(query, {"appointment_date": 1, "appointment_time": 1, "vehicle_number": 1}))
        
        rows = []
        for b in bookings:
            rows.append({
                "date": b.get("appointment_date"),
                "time": b.get("appointment_time"),
                "vehicle_number": b.get("vehicle_number")
            })
                    
        return jsonify(rows)
    except Exception as e:
        print(f"Error fetching slots: {e}")
        return jsonify([])

@app.route('/api/status', methods=['GET'])
def get_shop_status():
    db = get_db()
    row = db.shop_status.find_one({"id": 1})
    
    if row:
        row = serialize_db_row(row)
        row['is_busy'] = bool(row.get('is_busy'))
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
    db = get_db()
    user = db.users.find_one({"phone": phone})
    
    stamps = user.get('stamps', 0) if user else random.randint(0, 4)
    return jsonify({"stamps": stamps, "freeWash": stamps >= 5})

@app.route('/api/update-profile', methods=['POST'])
def update_user_profile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    phone = data.get('phone')
    email = data.get('email')
    user_id = session['user_id']
    
    db = get_db()
    try:
        # Check if email/phone already taken by another user
        existing = db.users.find_one({
            "$and": [
                {"$or": [{"email": email}, {"phone": phone}]},
                {"_id": {"$ne": ObjectId(user_id)}}
            ]
        })
        
        if existing:
             return jsonify({"success": False, "message": "Email or Phone already exists"}), 400

        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"phone": phone, "email": email}})
        
        session['user_phone'] = phone
        session['user_email'] = email
        
        return jsonify({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

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
        db = get_db()
        db.users.update_one({"_id": ObjectId(session['user_id'])}, {"$set": {"profile_pic": relative_path}})
        
        return jsonify({"success": True, "profile_pic": relative_path})
    
    return jsonify({"success": False, "message": "Upload failed"}), 400


@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    if 'user_id' not in session:
        return jsonify({"success": False}), 401
    
    user_id = session['user_id']
    db = get_db()
    db.notifications.update_many({"user_id": user_id}, {"$set": {"is_read": 1}})
    return jsonify({"success": True})

# =========================
# OTHER USER REQUESTED ROUTES
# =========================

@app.route("/api/add_vehicle", methods=["POST"])
@app.route("/add_vehicle", methods=["POST"])
def add_vehicle():
    data = request.json
    try:
        db = get_db()
        vehicle_doc = {
            "user_id": data.get("user_id"),
            "vehicle_number": data.get("vehicle_number"),
            "vehicle_type": data.get("vehicle_type"),
            "model": data.get("model"),
            "created_at": datetime.utcnow()
        }
        db.vehicles.insert_one(vehicle_doc)
        return jsonify({"success": True, "message": "Vehicle added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/update_profile", methods=["PUT"])
@app.route("/update_profile", methods=["PUT"])
def update_profile():
    data = request.json
    try:
        db = get_db()
        user_id = data.get("id")
        db.users.update_one(
            {"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id},
            {"$set": {"fullname": data.get("fullname"), "phone": data.get("phone")}}
        )
        return jsonify({"success": True, "message": "Profile updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/pay", methods=["POST"])
@app.route("/pay", methods=["POST"])
def make_payment():
    data = request.json
    try:
        db = get_db()
        payment_doc = {
            "booking_id": data.get("booking_id"),
            "amount": data.get("amount"),
            "payment_method": data.get("method"),
            "payment_status": 'paid',
            "created_at": datetime.utcnow()
        }
        db.payments.insert_one(payment_doc)
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
        db = get_db()
        packages = list(db.packages.find({"is_active": 1}).sort("price", 1))
        return jsonify(serialize_db_rows(packages))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/addons', methods=['GET'])
def get_addons():
    """Get all active add-ons"""
    try:
        db = get_db()
        addons = list(db.addons.find({"is_active": 1}).sort("price", 1))
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
        db = get_db()
        # Check if user already has an active subscription
        existing = db.subscriptions.find_one({
            "user_id": user_id, 
            "status": "active", 
            "end_date": {"$gte": datetime.utcnow().strftime('%Y-%m-%d')}
        })
        
        if existing:
            return jsonify({"success": False, "message": "You already have an active subscription"}), 400
        
        end_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
        sub_doc = {
            "user_id": user_id,
            "plan_name": 'Unlimited Club',
            "price": 999.00,
            "start_date": datetime.utcnow().strftime('%Y-%m-%d'),
            "end_date": end_date,
            "status": 'active',
            "created_at": datetime.utcnow()
        }
        result = db.subscriptions.insert_one(sub_doc)
        
        return jsonify({
            "success": True, 
            "message": "Subscription activated successfully!",
            "subscription_id": str(result.inserted_id)
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
        db = get_db()
        subscription = db.subscriptions.find_one({
            "user_id": user_id, 
            "status": "active", 
            "end_date": {"$gte": datetime.utcnow().strftime('%Y-%m-%d')}
        }, sort=[("end_date", -1)])
        
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
    db = get_db()
    try:
        loyalty = db.loyalty_points.find_one({"user_id": user_id})
        if not loyalty:
            loyalty = {"user_id": user_id, "total_washes": 0, "free_washes": 0, "points": 0}
            db.loyalty_points.insert_one(loyalty)
        
        return jsonify(serialize_db_row(loyalty))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/loyalty/update', methods=['POST'])
def update_loyalty():
    """Update loyalty points after completed wash"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    user_id = session['user_id']
    db = get_db()
    try:
        loyalty = db.loyalty_points.find_one({"user_id": user_id})
        if not loyalty:
            db.loyalty_points.insert_one({
                "user_id": user_id, 
                "total_washes": 1, 
                "free_washes": 0, 
                "points": 10, 
                "last_wash_date": datetime.utcnow().strftime('%Y-%m-%d')
            })
        else:
            total_washes = loyalty.get('total_washes', 0) + 1
            free_washes = loyalty.get('free_washes', 0)
            points = loyalty.get('points', 0) + 10
            
            if total_washes % 5 == 0:
                free_washes += 1
            
            db.loyalty_points.update_one(
                {"user_id": user_id}, 
                {"$set": {
                    "total_washes": total_washes, 
                    "free_washes": free_washes, 
                    "points": points, 
                    "last_wash_date": datetime.utcnow().strftime('%Y-%m-%d')
                }}
            )
        
        return jsonify({"success": True, "message": "Loyalty updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/stations', methods=['GET'])
def get_stations():
    """Get all stations with their current status"""
    try:
        db = get_db()
        stations = list(db.stations.find({}))
        # Join logic manual for MongoDB
        for s in stations:
            if s.get('current_booking_id'):
                booking = db.bookings.find_one({"_id": ObjectId(s['current_booking_id'])})
                if booking:
                    s['customer_name'] = booking.get('customer_name')
                    s['vehicle_number'] = booking.get('vehicle_number')
                    s['service_package'] = booking.get('service_package')
        
        return jsonify(serialize_db_rows(stations))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/stations/<station_id>/update', methods=['POST'])
def update_station_status(station_id):
    """Update station status (admin/staff only)"""
    role = session.get('role')
    if role not in ['admin', 'staff']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    db = get_db()
    try:
        db.stations.update_one(
            {"_id": ObjectId(station_id) if ObjectId.is_valid(station_id) else station_id},
            {"$set": {
                "status": data.get('status', 'free'),
                "current_vehicle": data.get('current_vehicle'),
                "current_booking_id": data.get('booking_id'),
                "updated_at": datetime.utcnow()
            }}
        )
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
    rating = data.get('rating')
    
    if not rating or rating < 1 or rating > 5:
        return jsonify({"success": False, "message": "Invalid rating"}), 400
    
    db = get_db()
    try:
        db.feedback.insert_one({
            "user_id": user_id,
            "booking_id": data.get('booking_id'),
            "rating": rating,
            "comment": data.get('comment', ''),
            "created_at": datetime.utcnow()
        })
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
    db = get_db()
    try:
        # Revenue
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
        rev_res = list(db.payments.aggregate(pipeline))
        revenue = rev_res[0]['total'] if rev_res else 0
        
        res = {
            "revenue": float(revenue),
            "total_bookings": db.bookings.count_documents({}),
            "total_users": db.users.count_documents({}),
            "active_subscriptions": db.subscriptions.count_documents({"status": "active"})
        }
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/bookings', methods=['GET'])
@admin_required
def get_admin_bookings():
    date = request.args.get('date')
    db = get_db()
    try:
        query = {}
        if date:
            query["appointment_date"] = date
            bookings = list(db.bookings.find(query).sort("appointment_time", 1))
        else:
            bookings = list(db.bookings.find(query).sort("appointment_date", -1).limit(100))
        
        return jsonify(serialize_db_rows(bookings))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/booking/status', methods=['POST'])
@admin_required
def update_booking_status():
    data = request.json
    booking_id = data.get('id')
    new_status = data.get('status')
    
    db = get_db()
    try:
        db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": new_status}})
        
        # Create notification for user
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
        if booking and booking.get('user_id'):
            user_id = booking['user_id']
            msg = f"Your {booking.get('service_package')} status changed to: {new_status}"
            db.notifications.insert_one({"user_id": user_id, "message": msg, "is_read": False, "created_at": datetime.utcnow()})
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_admin_users():
    db = get_db()
    try:
        users = list(db.users.find({}).sort("created_at", -1))
        return jsonify(serialize_db_rows(users))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    init_db()
    port = int(os.getenv('PORT', 5000))
    print(f"Server running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
