from app import app as application, init_db

# Ensure database is initialized on startup
try:
    init_db()
except Exception as e:
    print(f"Database init error: {e}")

if __name__ == "__main__":
    application.run()
