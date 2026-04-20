import mysql.connector
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
from decimal import Decimal

load_dotenv()

# MySQL Connection Details
def get_mysql_conn():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', 'Delvin@2005'),
        database=os.getenv('DB_NAME', 'car_wash')
    )

# MongoDB Connection Details
def get_mongo_db():
    client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/car_wash'))
    return client.get_database()

def serialize_value(val):
    if isinstance(val, (datetime, date)):
        return str(val)
    if isinstance(val, timedelta):
        return str(val)
    if isinstance(val, Decimal):
        return float(val)
    return val

def main():
    try:
        mongo_db = get_mongo_db()
        mysql_conn = get_mysql_conn()
        cursor = mysql_conn.cursor(dictionary=True)
        
        # Mapping for foreign keys
        user_id_map = {} # old_id -> new_oid_str
        booking_id_map = {} # old_id -> new_oid_str

        # 1. Migrate Users (Important for mapping)
        print("Migrating users...")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        user_coll = mongo_db['users']
        user_coll.delete_many({})
        for u in users:
            old_id = u['id']
            doc = {k: serialize_value(v) for k, v in u.items() if k != 'id'}
            res = user_coll.insert_one(doc)
            user_id_map[old_id] = str(res.inserted_id)
        print(f"Migrated {len(users)} users.")

        # 2. Migrate Bookings
        print("Migrating bookings...")
        cursor.execute("SELECT * FROM bookings")
        bookings = cursor.fetchall()
        booking_coll = mongo_db['bookings']
        booking_coll.delete_many({})
        for b in bookings:
            old_id = b['id']
            doc = {k: serialize_value(v) for k, v in b.items() if k != 'id'}
            # Map user_id
            if doc.get('user_id') in user_id_map:
                doc['user_id'] = user_id_map[doc['user_id']]
            res = booking_coll.insert_one(doc)
            booking_id_map[old_id] = str(res.inserted_id)
        print(f"Migrated {len(bookings)} bookings.")

        # 3. Migrate other tables
        other_tables = [
            'vehicles', 'services', 'admins', 'shop_status', 
            'notifications', 'payments', 'packages', 'addons', 
            'subscriptions', 'loyalty_points', 'stations', 'feedback'
        ]
        
        for table in other_tables:
            print(f"Migrating {table}...")
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                coll = mongo_db[table]
                coll.delete_many({})
                if not rows:
                    print(f"No data in {table}.")
                    continue
                
                mongo_rows = []
                for r in rows:
                    doc = {k: serialize_value(v) for k, v in r.items() if k != 'id'}
                    # Map common foreign keys
                    if 'user_id' in doc and doc['user_id'] in user_id_map:
                        doc['user_id'] = user_id_map[doc['user_id']]
                    if 'booking_id' in doc and doc['booking_id'] in booking_id_map:
                        doc['booking_id'] = booking_id_map[doc['booking_id']]
                    if 'current_booking_id' in doc and doc['current_booking_id'] in booking_id_map:
                        doc['current_booking_id'] = booking_id_map[doc['current_booking_id']]
                    
                    mongo_rows.append(doc)
                
                coll.insert_many(mongo_rows)
                print(f"Migrated {len(rows)} from {table}.")
            except Exception as e:
                print(f"Error migrating {table}: {e}")

        print("\nEnhanced migration completed successfully!")
        cursor.close()
        mysql_conn.close()
    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    main()
