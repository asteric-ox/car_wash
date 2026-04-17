"""
D2 Car Wash - Database Enhancement Script
Adds new tables for gaming-inspired features
"""

import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', 'Delvin@2005'),
        database=os.getenv('DB_NAME', 'car_wash')
    )

def enhance_database():
    conn = get_db()
    cursor = conn.cursor()
    
    print("🚀 Starting D2 Car Wash Database Enhancement...")
    
    # 1. Add profile_pic column to users if not exists
    try:
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS profile_pic VARCHAR(255) DEFAULT NULL
        """)
        print("✅ Added profile_pic column to users table")
    except Exception as e:
        print(f"⚠️  profile_pic column might already exist: {e}")
    
    # 2. Create packages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            duration_minutes INT DEFAULT 30,
            features JSON,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created packages table")
    
    # 3. Create addons table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS addons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            icon VARCHAR(50),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created addons table")
    
    # 4. Create appointment_addons junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointment_addons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            addon_id INT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY (addon_id) REFERENCES addons(id) ON DELETE CASCADE
        )
    """)
    print("✅ Created appointment_addons table")
    
    # 5. Create subscriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            plan_name VARCHAR(100) DEFAULT 'Unlimited Club',
            price DECIMAL(10, 2) DEFAULT 999.00,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status ENUM('active', 'expired', 'cancelled') DEFAULT 'active',
            auto_renew BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("✅ Created subscriptions table")
    
    # 6. Create loyalty_points table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loyalty_points (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            total_washes INT DEFAULT 0,
            free_washes INT DEFAULT 0,
            points INT DEFAULT 0,
            last_wash_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user (user_id)
        )
    """)
    print("✅ Created loyalty_points table")
    
    # 7. Create stations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            station_name VARCHAR(100) NOT NULL,
            status ENUM('free', 'occupied', 'maintenance') DEFAULT 'free',
            current_booking_id INT NULL,
            current_vehicle VARCHAR(255),
            estimated_completion TIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (current_booking_id) REFERENCES bookings(id) ON DELETE SET NULL
        )
    """)
    print("✅ Created stations table")
    
    # 8. Create feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            booking_id INT,
            rating INT CHECK (rating BETWEEN 1 AND 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL
        )
    """)
    print("✅ Created feedback table")
    
    # 9. Seed packages data
    cursor.execute("SELECT COUNT(*) FROM packages")
    if cursor.fetchone()[0] == 0:
        packages_data = [
            ('Basic Wash', 'Exterior wash with foam', 200.00, 20, '["Foam Wash", "Tire Cleaning", "Quick Dry"]'),
            ('Normal', 'Interior + Exterior cleaning', 350.00, 30, '["Foam Wash", "Interior Vacuum", "Dashboard Polish", "Tire Shine"]'),
            ('Super', 'Deep cleaning package', 450.00, 45, '["Premium Foam", "Deep Interior Clean", "Dashboard Polish", "Tire Shine", "Air Freshener"]'),
            ('Premium', 'Complete detailing', 600.00, 60, '["Premium Foam", "Deep Interior Clean", "Dashboard Polish", "Tire Shine", "Engine Cleaning", "Wax Coating"]'),
            ('Premium Plus', 'Ultimate luxury treatment', 800.00, 90, '["Premium Foam", "Deep Interior Clean", "Dashboard Polish", "Tire Shine", "Engine Cleaning", "Ceramic Coating", "Leather Treatment", "Headlight Restoration"]')
        ]
        cursor.executemany("""
            INSERT INTO packages (name, description, price, duration_minutes, features) 
            VALUES (%s, %s, %s, %s, %s)
        """, packages_data)
        print("✅ Seeded packages data")
    
    # 10. Seed addons data
    cursor.execute("SELECT COUNT(*) FROM addons")
    if cursor.fetchone()[0] == 0:
        addons_data = [
            ('Wax Coating', 'Premium wax protection', 150.00, 'fa-shield'),
            ('Engine Cleaning', 'Deep engine bay cleaning', 200.00, 'fa-engine'),
            ('Ceramic Coating', 'Long-lasting ceramic protection', 500.00, 'fa-gem'),
            ('Headlight Restoration', 'Crystal clear headlights', 100.00, 'fa-lightbulb'),
            ('Leather Treatment', 'Premium leather conditioning', 180.00, 'fa-couch'),
            ('Odor Removal', 'Professional odor elimination', 120.00, 'fa-spray-can'),
            ('Pet Hair Removal', 'Specialized pet hair cleaning', 100.00, 'fa-paw'),
            ('Scratch Removal', 'Minor scratch buffing', 250.00, 'fa-magic')
        ]
        cursor.executemany("""
            INSERT INTO addons (name, description, price, icon) 
            VALUES (%s, %s, %s, %s)
        """, addons_data)
        print("✅ Seeded addons data")
    
    # 11. Seed stations data
    cursor.execute("SELECT COUNT(*) FROM stations")
    if cursor.fetchone()[0] == 0:
        stations_data = [
            ('Station Alpha', 'free'),
            ('Station Beta', 'free'),
            ('Station Gamma', 'free'),
            ('Station Delta', 'free')
        ]
        cursor.executemany("""
            INSERT INTO stations (station_name, status) 
            VALUES (%s, %s)
        """, stations_data)
        print("✅ Seeded stations data")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n🎉 Database enhancement completed successfully!")
    print("📊 New tables added:")
    print("   - packages")
    print("   - addons")
    print("   - appointment_addons")
    print("   - subscriptions")
    print("   - loyalty_points")
    print("   - stations")
    print("   - feedback")

if __name__ == "__main__":
    try:
        enhance_database()
    except Exception as e:
        print(f"❌ Error: {e}")
