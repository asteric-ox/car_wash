-- D2 Car Wash - Supabase (PostgreSQL) Schema Setup
-- Paste this into the Supabase SQL Editor

-- 1. Create Custom Types
CREATE TYPE user_role AS ENUM ('admin', 'staff', 'customer', 'master');
CREATE TYPE user_status AS ENUM ('active', 'inactive');
CREATE TYPE subscription_status AS ENUM ('active', 'expired', 'cancelled');
CREATE TYPE station_status AS ENUM ('free', 'occupied', 'maintenance');

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    fullname VARCHAR(255),
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50) UNIQUE,
    password VARCHAR(255),
    password_hash VARCHAR(255),
    role user_role DEFAULT 'customer',
    status user_status DEFAULT 'active',
    stamps INT DEFAULT 0,
    profile_pic VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Vehicles Table
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    vehicle_number VARCHAR(50),
    vehicle_type VARCHAR(50),
    model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Services Table
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

-- 5. Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
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
    is_pickup BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'Pending',
    assigned_staff INT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Admins Table
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'staff',
    token VARCHAR(255) NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Shop Status Table
CREATE TABLE IF NOT EXISTS shop_status (
    id INT PRIMARY KEY,
    is_busy BOOLEAN DEFAULT FALSE,
    current_vehicle VARCHAR(255),
    message VARCHAR(255),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Payments Table
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2),
    total_price DECIMAL(10, 2),
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) DEFAULT 'paid',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Packages Table
CREATE TABLE IF NOT EXISTS packages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    duration_minutes INT DEFAULT 30,
    features JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Addons Table
CREATE TABLE IF NOT EXISTS addons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    icon VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Appointment Addons Junction Table
CREATE TABLE IF NOT EXISTS appointment_addons (
    id SERIAL PRIMARY KEY,
    booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,
    addon_id INT REFERENCES addons(id) ON DELETE CASCADE,
    price DECIMAL(10, 2) NOT NULL
);

-- 13. Subscriptions Table
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(100) DEFAULT 'Unlimited Club',
    price DECIMAL(10, 2) DEFAULT 999.00,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status subscription_status DEFAULT 'active',
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. Loyalty Points Table
CREATE TABLE IF NOT EXISTS loyalty_points (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    total_washes INT DEFAULT 0,
    free_washes INT DEFAULT 0,
    points INT DEFAULT 0,
    last_wash_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. Stations Table
CREATE TABLE IF NOT EXISTS stations (
    id SERIAL PRIMARY KEY,
    station_name VARCHAR(100) NOT NULL,
    status station_status DEFAULT 'free',
    current_booking_id INT REFERENCES bookings(id) ON DELETE SET NULL,
    current_vehicle VARCHAR(255),
    estimated_completion TIME,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 16. Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    booking_id INT REFERENCES bookings(id) ON DELETE SET NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Data
INSERT INTO services (service_name, price) VALUES 
('Basic Wash', 200.00), ('Normal', 350.00), ('Super', 450.00), ('Premium', 600.00), ('Premium Plus', 800.00)
ON CONFLICT DO NOTHING;

INSERT INTO shop_status (id, is_busy, message) VALUES (1, FALSE, 'Ready to Shine!')
ON CONFLICT (id) DO UPDATE SET message = EXCLUDED.message;

INSERT INTO packages (name, description, price, duration_minutes, features) VALUES 
('Basic Wash', 'Exterior wash', 200.00, 20, '["Foam Wash"]'),
('Premium Plus', 'Luxury', 800.00, 90, '["Ceramic Coating"]')
ON CONFLICT DO NOTHING;
