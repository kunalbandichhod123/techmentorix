from app.db import SessionLocal
from app.models import User

def create_user():
    db = SessionLocal()
    # CHANGE THIS to the exact phone number you are using to login
    my_phone = "9028023597" 
    
    # Check if exists
    existing = db.query(User).filter(User.phone == my_phone).first()
    if not existing:
        new_user = User(phone=my_phone, role="doctor") # or "patient"
        db.add(new_user)
        db.commit()
        print(f"Success! User {my_phone} created. You can now log in.")
    else:
        print("User already exists.")
    db.close()

if __name__ == "__main__":
    create_user()