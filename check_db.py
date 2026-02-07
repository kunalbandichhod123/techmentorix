from app.db import SessionLocal, engine
from app.models import User
from sqlalchemy import inspect

def diagnostic():
    db = SessionLocal()
    inspector = inspect(engine)
    
    print("--- 1. DATABASE COLUMNS ---")
    columns = [c['name'] for c in inspector.get_columns("users")]
    print(f"Columns in 'users' table: {columns}")
    
    print("\n--- 2. REGISTERED USERS ---")
    users = db.query(User).all()
    if not users:
        print("No users found in the database. This is why you are getting a 401.")
    for u in users:
        # We use getattr to avoid crashing if the 'phone' column is missing
        phone_val = getattr(u, 'phone', 'COLUMN MISSING')
        email_val = getattr(u, 'email', 'COLUMN MISSING')
        print(f"ID: {u.id} | Role: {u.role} | Phone: {phone_val} | Email: {email_val}")
    
    db.close()

if __name__ == "__main__":
    diagnostic()