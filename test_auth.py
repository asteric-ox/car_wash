import requests

URL = "http://localhost:5000"

def test_login():
    session = requests.Session()
    # Try login
    data = {"identifier": "test@test.com", "password": "password123"}
    res = session.post(f"{URL}/api/login", json=data)
    print("Login Response:", res.json())
    
    # Check auth
    res = session.get(f"{URL}/api/check-auth")
    print("Check Auth Response:", res.json())

if __name__ == "__main__":
    # First register if not exist
    reg_data = {"fullname": "Test User", "email": "test@test.com", "phone": "1234567890", "password": "password123"}
    r = requests.post(f"{URL}/api/register", json=reg_data)
    print("Register Response:", r.json())
    
    test_login()
