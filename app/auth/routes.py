from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.otp_service import send_otp, verify_otp
from app.auth.jwt import create_token
from app.db import SessionLocal
from app.models import Patient, MealPlan, User

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------- DB DEP ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- SCHEMAS ----------------
class PhoneRequest(BaseModel):
    phone: str


class VerifyRequest(BaseModel):
    phone: str
    otp: str


# ---------------- SEND OTP ----------------
@router.post("/send-otp")
def send_otp_api(data: PhoneRequest):
    send_otp(data.phone)
    return {"message": "OTP sent"}


# ---------------- VERIFY OTP ----------------
class VerifyOtpRequest(BaseModel):  
    phone: str
    otp: str


from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.otp_service import send_otp, verify_otp
from app.auth.jwt import create_token
from app.db import SessionLocal
from app.models import Patient, MealPlan

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------- DB DEP ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- SCHEMAS ----------------
class PhoneRequest(BaseModel):
    phone: str


class VerifyRequest(BaseModel):
    phone: str
    otp: str


# ---------------- SEND OTP ----------------
@router.post("/send-otp")
def send_otp_api(data: PhoneRequest):
    send_otp(data.phone)
    return {"message": "OTP sent"}


# ---------------- VERIFY OTP ----------------
class VerifyOtpRequest(BaseModel):  
    phone: str
    otp: str


@router.post("/verify-otp")
def verify_otp_route(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    if not verify_otp(data.phone, data.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # 1. Ensure user exists in the 'users' table (Common for both)
    user = db.query(User).filter(User.phone == data.phone).first()
    
    if not user:
        # Default to doctor for testing, or handle registration logic here
        user = User(phone=data.phone, role="doctor") 
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. If they are a patient, ensure they exist in 'patients' table
    patient = db.query(Patient).filter(Patient.phone == data.phone).first()
    if not patient and user.role == "patient":
        patient = Patient(name=data.phone, phone=data.phone, age=0, gender="N/A", height=0, weight=0)
        db.add(patient)
        db.commit()

    # 3. Create token with the role
    access_token = create_token(data.phone, role=user.role)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }