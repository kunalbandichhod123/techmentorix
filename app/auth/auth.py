# app/auth/auth.py
import os
import random
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text  # <--- Added missing import
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import User, Patient
from app.services.otp_service import send_otp, verify_otp
from app.services.email_service import send_email_otp

load_dotenv()

otp_storage = {} 

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

# --- CONFIGURATION ---
SECRET_KEY = os.getenv("JWT_SECRET", "your_secret_key_here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

# Password Hashing Config
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme (Points to the login endpoint, though we support two)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/doctor/login")

router = APIRouter()

# --- DATABASE DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- REQUEST MODELS ---
class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str

class OtpRequest(BaseModel):
    phone: str

class DoctorLoginRequest(BaseModel):
    email: EmailStr
    password: str

class DoctorRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    phone: Optional[str] = None

# --- HELPER FUNCTIONS ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Validates the token and retrieves the current user.
    Supports both Email (Doctor) and Phone (Patient) tokens.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # The 'sub' claim could be an Email (Doctor) OR a Phone Number (Patient)
        username: str = payload.get("sub")
        role: str = payload.get("role")
        
        if username is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Check User based on role
    if role == "doctor":
        user = db.query(User).filter(User.email == username).first()
    else:
        # Patient (Phone)
        user = db.query(User).filter(User.phone == username).first()
        # Fallback for phone formatting issues
        if not user and username.startswith("+91"):
            alt_phone = username.replace("+91", "")
            user = db.query(User).filter(User.phone == alt_phone).first()

    if user is None:
        raise credentials_exception
        
    return user


# ==========================================
# 🩺 DOCTOR AUTH ROUTES (Email & Password)
# ==========================================

@router.post("/doctor/register")
def register_doctor(data: DoctorRegisterRequest, db: Session = Depends(get_db)):
    # 1. Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Hash Password
    hashed_pwd = get_password_hash(data.password)

    # 3. Create User
    new_doctor = User(
        email=data.email,
        password_hash=hashed_pwd,
        phone=data.phone, # Optional
        role="doctor"
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    return {"message": "Doctor registered successfully. Please login."}

@router.post("/doctor/login")
def login_doctor(data: DoctorLoginRequest, db: Session = Depends(get_db)):
    # 1. Find User by Email
    user = db.query(User).filter(User.email == data.email).first()
    
    # 2. Verify Password & Role
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Not authorized as doctor")

    # 3. Generate Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": "doctor", "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "role": "doctor"}


# ==========================================
# 🧘 PATIENT AUTH ROUTES (Phone & OTP)
# ==========================================

@router.post("/send-otp")
def send_otp_route(data: dict):
    phone = data.get("phone")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone required")
    
    # Call the service
    send_otp(phone)
    return {"message": "OTP sent successfully"}


@router.post("/verify-otp")
def verify_otp_route(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    # 1. Verify OTP using Service
    if not verify_otp(data.phone, data.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # 2. Ensure User Exists in DB (Auto-Register Patient)
    user = db.query(User).filter(User.phone == data.phone).first()
    if not user:
        # Default new users to 'patient'
        user = User(phone=data.phone, role="patient") 
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Generate Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Note: 'sub' is phone for patients
    access_token = create_access_token(
        data={"sub": data.phone, "role": user.role, "user_id": user.id}, 
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "role": user.role}


@router.post("/verify-patient-registration")
def verify_patient_reg(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Used by DOCTOR to verify a patient's phone before filling the form.
    Checks if patient already exists in the Patient table.
    """
    if not verify_otp(data.phone, data.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    existing = db.query(Patient).filter(Patient.phone == data.phone).first()
    if existing:
        return {"status": "exists", "patient_id": existing.id, "name": existing.name}

    return {"status": "verified", "phone": data.phone}

@router.post("/logout")
def logout():
    return {"message": "Logged out"}

@router.post("/doctor/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Check if doctor exists
    user = db.query(User).filter(User.email == data.email, User.role == "doctor").first()
    if not user:
        # Security: Don't reveal if email exists or not
        return {"message": "If the email exists, an OTP has been sent."}

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"
    
    # Save OTP to memory (linked to email)
    otp_storage[data.email] = otp
    
    # Send Email
    email_sent = send_email_otp(data.email, otp)
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send email.")

    return {"message": "OTP sent to your email."}

# 2. RESET PASSWORD
@router.post("/doctor/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Verify OTP
    stored_otp = otp_storage.get(data.email)
    
    if not stored_otp or stored_otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Find User
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hash new password
    user.password_hash = get_password_hash(data.new_password)
    db.commit()

    # Clear used OTP
    del otp_storage[data.email]

    return {"message": "Password reset successfully. Please login."}

@router.get("/doctor/profile")
def get_doctor_profile(
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    # ---------------------------------------------------------
    # 🔐 RLS STEP: Set the Doctor's Email Key
    # ---------------------------------------------------------
    # This tells Postgres: "The person asking is this specific doctor"
    db.execute(
        text(f"SET app.current_user_email = '{current_user.email}'")
    )
    
    # ---------------------------------------------------------
    # 🔎 QUERY: Now RLS protects the query
    # ---------------------------------------------------------
    # This will strictly return ONLY the logged-in user's data
    user_data = db.query(User).filter(User.email == current_user.email).first()
    
    return user_data