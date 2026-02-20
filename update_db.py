import mysql.connector
import os
from dotenv import load_dotenv
import time

load_dotenv()

def update_database():
    conn = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASS', 'Delvin@2005'),
            database=os.getenv('DB_NAME', 'car_wash')
        )
        # Use buffered cursor to handle unread results
        cursor = conn.cursor(buffered=True)

        print("Checking for missing columns...")

        def check_and_add_column(table, column, definition):
            try:
                print(f"Checking for '{column}' in '{table}'...")
                cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
                cursor.fetchone() # Consume result
                print(f"'{column}' column exists.")
            except mysql.connector.Error as err:
                 # Error Code: 1054. Unknown column
                if err.errno == 1054:
                    print(f"Adding '{column}' column...")
                    try:
                        sql = f"ALTER TABLE {table} ADD COLUMN {definition}"
                        print(f"Executing: {sql}")
                        cursor.execute(sql)
                        print(f"'{column}' column added.")
                    except mysql.connector.Error as add_err:
                        print(f"Error adding column '{column}': {add_err}")
                else:
                    print(f"Error checking column '{column}': {err}")

        # Check for 'stamps'
        check_and_add_column('users', 'stamps', "stamps INT DEFAULT 0")

        # Check for 'role'
        check_and_add_column('users', 'role', "role ENUM('admin','staff','customer') DEFAULT 'customer'")

        # Check for 'status'
        check_and_add_column('users', 'status', "status ENUM('active','inactive') DEFAULT 'active'")
            
        # Check for 'password_hash'
        check_and_add_column('users', 'password_hash', "password_hash VARCHAR(255)")

         # Check for 'created_at' in bookings if missing 
        check_and_add_column('bookings', 'created_at', "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")


        # Re-check columns just in case
        cursor.execute("DESCRIBE users")
        columns = [row[0] for row in cursor.fetchall()]
        print("Users Columns:", columns)

        conn.commit()
        cursor.close()
        conn.close()
        print("Database updated successfully!")

    except Exception as e:
        print(f"Error: {e}")
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    update_database()
