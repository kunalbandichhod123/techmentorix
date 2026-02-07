from jose import jwt
from datetime import datetime, timedelta
import os

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET not loaded from .env")

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/verify-otp")

# ---------------- TOKEN ----------------
# app/auth/jwt.py
def create_token(phone: str, role: str):
    # Ensure the 'role' is included in the payload
    payload = {
        "sub": phone,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ---------------- DB ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- AUTH DEP ----------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone = payload.get("sub")
        if phone is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Check in the User table
        user = db.query(User).filter(User.phone == phone).first()
        
        # If the user isn't in the 'users' table, check if they are a 'patient'
        # This handles the case where patients log in but aren't in the 'users' table yet
        if not user:
             raise HTTPException(status_code=401, detail="User record not found")

        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")