# 🚀 D2 CAR WASH - Premium Auto Detailing Platform

![Version](https://img.shields.io/badge/version-2.0-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange)
![Status](https://img.shields.io/badge/status-active-success)

## 🎮 Gaming-Inspired Premium Car Wash Platform

D2 Car Wash is a state-of-the-art, full-stack web application featuring a **gaming-inspired UI** with premium animations, real-time station tracking, loyalty rewards, and subscription management.

---

## ✨ KEY FEATURES

### 🎨 Gaming-Inspired UI
- **Cinematic BMW Intro Animation** - Stunning glass-breaking effect with brand reveal
- **Neon Glow Effects** - Cyberpunk-style hover animations
- **Particle System** - Water droplet animations
- **Ripple Effects** - Interactive button feedback
- **Smooth Transitions** - Premium micro-interactions

### 🚗 Core Functionality
- **Smart Booking System** - Multi-step wizard with real-time validation
- **Live Station Status** - Real-time tracking of 4 wash stations
- **Loyalty Rewards** - "Wash 5 Times, Get 1 Free" program
- **Unlimited Club** - ₹999/month subscription with unlimited washes
- **Pickup Service** - GPS-based pickup requests with Google Maps
- **Feedback System** - Customer reviews and ratings

### 👤 User Management
- **Secure Authentication** - Password hashing with Werkzeug
- **Profile Management** - Update email, phone, profile picture
- **Session Management** - 7-day persistent sessions



---

## 🛠 TECH STACK

### Backend
- **Flask** - Python web framework
- **MySQL** - Relational database
- **Flask-CORS** - Cross-origin resource sharing
- **Flask-SocketIO** - Real-time communication (future)
- **Werkzeug** - Password hashing
- **Pillow** - Image processing
- **Python-dotenv** - Environment variables

### Frontend
- **HTML5** - Semantic markup
- **Tailwind CSS** - Utility-first CSS framework
- **Vanilla JavaScript** - No framework dependencies
- **Leaflet.js** - Interactive maps
- **Font Awesome** - Icon library
- **Google Fonts** - Outfit & Syncopate typography

### Database Schema
- `users` - Customer, staff, admin accounts
- `bookings` - Appointment records
- `packages` - Service packages with pricing
- `addons` - Additional services
- `subscriptions` - Unlimited Club memberships
- `loyalty_points` - Rewards tracking
- `stations` - Wash station status
- `feedback` - Customer reviews
- `payments` - Transaction records
- `notifications` - User notifications

---

## 📦 INSTALLATION

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- pip (Python package manager)

### Step 1: Clone Repository
```bash
cd "c:/CAR WASH DU"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment
Create/edit `.env` file:
```env
DB_HOST=localhost
DB_USER=root
DB_PASS=your_password
DB_NAME=car_wash
SECRET_KEY=your_secret_key
MAIL_USER=your_email@gmail.com
MAIL_PASS=your_app_password
PORT=5000
```

### Step 4: Initialize Database
```bash
python enhance_database.py
```

This will:
- Create all required tables
- Seed initial data (packages, addons, stations)
- Set up default admin account

### Step 5: Run Application
```bash
python app.py
```

Server will start at: `http://localhost:5000`

---

## 🎯 USAGE GUIDE

### For Customers

#### 1. Register/Login
- Click "Login" button in navbar
- Toggle to "Register" tab
- Fill in details with country code
- Login with email or phone

#### 2. Book a Wash
- Click "Book Appointment"
- Select vehicle type
- Choose service package
- Pick date & time
- Add optional add-ons
- Confirm booking

#### 3. Request Pickup
- Click "Request Pickup"
- Allow location access or search address
- Confirm location on map
- Staff will be notified

#### 4. Track Loyalty
- View loyalty card in dashboard
- Earn stamps for each wash
- Get 1 free wash every 5 washes

#### 5. Subscribe to Unlimited Club
- View subscription card
- Click "Subscribe Now"
- Pay ₹999 for 30 days
- Enjoy unlimited basic washes



---

## 🎨 GAMING UI COMPONENTS

### Station Status Cards
```javascript
// Usage in frontend
const stations = await fetch('/api/stations').then(r => r.json());
const html = stations.map(station => 
    window.GamingUI.createStationCard(station)
).join('');
```

### Loyalty Card
```javascript
const loyalty = await fetch('/api/loyalty/status').then(r => r.json());
const html = window.GamingUI.createLoyaltyCard(
    loyalty.total_washes,
    loyalty.free_washes
);
```

### Subscription Card
```javascript
const subscription = await fetch('/api/subscription/status').then(r => r.json());
const html = window.GamingUI.createSubscriptionCard(subscription);
```

### Trigger Confetti
```javascript
// On successful action
window.GamingUI.triggerConfetti();
```

### Animated Counter
```javascript
const element = document.getElementById('revenue-counter');
window.GamingUI.animateCounter(element, 50000, 2000);
```

---

## 🔌 API ENDPOINTS

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - User login

### Bookings
- `POST /api/book` - Create booking
- `GET /api/my_bookings/<user_id>` - Get user bookings


### Packages & Add-ons
- `GET /api/packages` - Get all packages
- `GET /api/addons` - Get all add-ons

### Subscriptions
- `POST /api/subscribe` - Create subscription
- `GET /api/subscription/status` - Check subscription

### Loyalty
- `GET /api/loyalty/status` - Get loyalty points
- `POST /api/loyalty/update` - Update after wash

### Stations
- `GET /api/stations` - Get all stations


### Feedback
- `POST /api/feedback` - Submit feedback



### Utilities
- `GET /api/status` - Shop status
- `GET /api/slots` - Available slots
- `GET /api/weather` - Weather forecast
- `GET /api/notifications` - User notifications

---

## 🎨 COLOR PALETTE

```css
/* Brand Colors */
--brand-dark: #0f172a;      /* Dark background */
--brand-primary: #06b6d4;   /* Cyan - Primary actions */
--brand-secondary: #64748b; /* Slate - Secondary text */
--brand-accent: #f59e0b;    /* Amber - Highlights */

/* Status Colors */
--neon-green: #10b981;      /* Free/Success */
--neon-red: #ef4444;        /* Occupied/Error */
--neon-yellow: #f59e0b;     /* Maintenance/Warning */
--gold: #fbbf24;            /* Premium/Subscription */
```

---

## 📱 RESPONSIVE DESIGN

- **Mobile First** - Optimized for mobile devices
- **Breakpoints**:
  - Mobile: < 768px
  - Tablet: 768px - 1024px
  - Desktop: > 1024px
- **Touch Friendly** - Large tap targets
- **Adaptive Layout** - Grid system adjusts

---

## 🔒 SECURITY FEATURES

- **Password Hashing** - Werkzeug secure hashing
- **Session Management** - HTTP-only cookies
- **SQL Injection Prevention** - Parameterized queries
- **XSS Protection** - Input sanitization
- **CORS Configuration** - Controlled access
- **Role-Based Access** - Authorization checks

---

## 🚀 PERFORMANCE OPTIMIZATIONS

- **Lazy Loading** - Images load on demand
- **Minified Assets** - Compressed CSS/JS
- **Database Indexing** - Fast queries
- **Caching** - Browser caching enabled
- **Optimized Images** - WebP format support

---

## 🐛 TROUBLESHOOTING

### Database Connection Error
```bash
# Check MySQL service
mysql -u root -p

# Verify credentials in .env
DB_HOST=localhost
DB_USER=root
DB_PASS=your_password
```

### Port Already in Use
```bash
# Change port in .env
PORT=5001

# Or kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Email Not Sending
```bash
# Verify Gmail App Password
# Enable 2FA on Gmail
# Generate App Password
# Update MAIL_PASS in .env
```

### Gaming UI Not Loading
```bash
# Check browser console
# Verify gaming_ui.js is loaded
# Clear browser cache
# Hard refresh (Ctrl+Shift+R)
```

---

### For Admins

#### 1. Access Admin Portal
- Click "Staff/Admin" in the login modal.
- Use Master Credentials:
  - **Email**: `delvindavis031@gmail.com`
  - **Password**: `Delvin@2005`
- This grants full access to analytics, bookings, and user management.

#### 2. Manage Bookings
- View live dashboard for recent bookings.
- Change status (Approved, Washing, Drying, Completed).
- Real-time notifications are sent to customers on status change.

#### 3. Shop Status Control
- Set the main wash station as "Busy" or "Free".
- Enter the vehicle number being washed to display it on the homepage for all users.

---

## 📈 FUTURE ENHANCEMENTS

### Phase 1 (Planned)
- [ ] Real-time WebSocket updates
- [ ] Push notifications
- [ ] Payment gateway integration (Razorpay)
- [ ] SMS notifications
- [ ] WhatsApp integration

### Phase 2 (Future)
- [ ] Mobile app (React Native)
- [ ] Voice booking
- [ ] AR car preview
- [ ] Multi-language support
- [ ] Dark/Light mode toggle

### Phase 3 (Advanced)
- [ ] AI-powered recommendations
- [ ] Predictive maintenance alerts
- [ ] Franchise management
- [ ] Multi-location support
- [ ] Advanced analytics dashboard

---

## 👥 TEAM

- **Developer**: Delvin Davis
- **Company**: D2 Car Wash
- **Location**: Thrissur, Kerala
- **Contact**: delvindavis031@gmail.com
- **Phone**: +91 8590624912

---

## 📄 LICENSE

Copyright © 2026 D2 Car Wash. All rights reserved.

---

## 🙏 ACKNOWLEDGMENTS

- **Tailwind CSS** - Utility-first CSS framework
- **Font Awesome** - Icon library
- **Leaflet.js** - Interactive maps
- **Google Fonts** - Typography
- **Flask** - Python web framework

---

## 📞 SUPPORT

For support, email delvindavis031@gmail.com or call +91 8590624912.

---

**Built with ❤️ by D2 Car Wash Team**

*Experience the Ultimate Shine* ✨
