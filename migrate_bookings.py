
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', 'Delvin@2005'),
        database=os.getenv('DB_NAME', 'car_wash')
    )
    cursor = conn.cursor()

    # 1. Update Users Table
    print("Migrating Users Table...")
    try:
        # Check if 'role' column exists
        cursor.execute("SHOW COLUMNS FROM users LIKE 'role'")
        if not cursor.fetchone():
            print("Adding 'role' column to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN role ENUM('admin','staff','customer') DEFAULT 'customer'")
        
        # Check if 'status' column exists
        cursor.execute("SHOW COLUMNS FROM users LIKE 'status'")
        if not cursor.fetchone():
            print("Adding 'status' column to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN status ENUM('active','inactive') DEFAULT 'active'")

        # Ensure fullname column exists (might be 'name' currently)
        cursor.execute("SHOW COLUMNS FROM users LIKE 'fullname'")
        if not cursor.fetchone():
            # if name exists, maybe rename it or just add fullname
            cursor.execute("SHOW COLUMNS FROM users LIKE 'name'")
            if cursor.fetchone():
                print("Renaming 'name' to 'fullname'...")
                cursor.execute("ALTER TABLE users CHANGE COLUMN name fullname VARCHAR(100)")
            else:
                 print("Adding 'fullname' column...")
                 cursor.execute("ALTER TABLE users ADD COLUMN fullname VARCHAR(100)")

    except mysql.connector.Error as err:
        print(f"Error migrating users: {err}")

    # 2. Update Bookings Table
    print("Migrating Bookings Table...")
    try:
        # Check for assigned_staff
        cursor.execute("SHOW COLUMNS FROM bookings LIKE 'assigned_staff'")
        if not cursor.fetchone():
            print("Adding 'assigned_staff' column to bookings...")
            cursor.execute("ALTER TABLE bookings ADD COLUMN assigned_staff INT")
            # cursor.execute("ALTER TABLE bookings ADD FOREIGN KEY (assigned_staff) REFERENCES users(id)") # Optional/Risky if data mismatch
        
        # Check for service_type (might be service_package)
        cursor.execute("SHOW COLUMNS FROM bookings LIKE 'service_type'")
        if not cursor.fetchone():
             # service_package exists, maybe just alias or ignore? User asked for service_type
             # I'll add it if missing, or we assume service_package is enough.
             # Let's check if service_package exists
             cursor.execute("SHOW COLUMNS FROM bookings LIKE 'service_package'")
             if not cursor.fetchone():
                 cursor.execute("ALTER TABLE bookings ADD COLUMN service_type VARCHAR(100)")
             else:
                 print("Column 'service_package' exists, treating as 'service_type'.")

    except mysql.connector.Error as err:
        print(f"Error migrating bookings: {err}")

    # 3. Create Default Admin if not exists in users
    try:
        cursor.execute("SELECT * FROM users WHERE email = 'admin@d2.com'")
        if not cursor.fetchone():
            print("Creating default admin user...")
            from werkzeug.security import generate_password_hash
            pw_hash = generate_password_hash("admin123")
            cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES ('Master Admin', 'admin@d2.com', %s, 'admin')", (pw_hash,))
    except Exception as e:
        print(f"Error creating default admin: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
