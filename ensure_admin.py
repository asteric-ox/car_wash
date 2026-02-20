import mysql.connector
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', 'Delvin@2005'),
        database=os.getenv('DB_NAME', 'car_wash')
    )
    cursor = conn.cursor()
    
    email = 'admin@d2.com'
    password = 'admin123'
    hashed_pw = generate_password_hash(password)
    
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    
    if cursor.fetchone():
        print(f"Updating existing admin {email}...")
        # Update both password fields for compatibility
        cursor.execute("UPDATE users SET role='admin', password=%s, password_hash=%s WHERE email=%s", (hashed_pw, hashed_pw, email))
    else:
        print(f"Creating new admin {email}...")
        # Insert all fields to satisfy constraints
        cursor.execute("""
            INSERT INTO users (fullname, name, email, phone, password, password_hash, role) 
            VALUES ('Master Admin', 'Master Admin', %s, '9999999999', %s, %s, 'admin')
        """, (email, hashed_pw, hashed_pw))
        
    conn.commit()
    conn.close()
    print("Admin account configured successfully.")
except Exception as e:
    print(f"Error: {e}")
