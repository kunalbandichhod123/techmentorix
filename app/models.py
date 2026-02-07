from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # ---------------------------------------------------
    # 1. NEW FIELDS FOR HYBRID LOGIN
    # ---------------------------------------------------
    # Phone is now nullable (Patients need it, Doctors might not)
    phone = Column(String, unique=True, index=True, nullable=True)
    
    # Email is for Doctors (Nullable because Patients won't have it)
    email = Column(String, unique=True, index=True, nullable=True)
    
    # Password is for Doctors (Patients use OTP)
    password_hash = Column(String, nullable=True)
    
    # Role is still required ("doctor" or "patient")
    role = Column(String, default="patient")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patients = relationship("Patient", back_populates="doctor")

# ... (Keep your existing Patient and MealPlan classes exactly the same below) ...
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    age = Column(Integer)
    gender = Column(String)
    height = Column(Float, default=0.0)
    weight = Column(Float, default=0.0)
    
    # --- Ayurvedic Fields ---
    prakriti = Column(String, nullable=True) # e.g., "Vata-Pitta"
    disease = Column(String, nullable=True)  # This is "Vikriti"
    
    # 🆕 NEW FIELDS (Add these so PDF can print them)
    ama = Column(String, default="No", nullable=True)      # e.g., "High", "Low"
    agni = Column(String, default="Balanced", nullable=True) # e.g., "Manda", "Tikshna"
    roga = Column(String, nullable=True)     # Specific Diagnosis
    
    doctor_id = Column(Integer, ForeignKey("users.id"))
    doctor = relationship("User", back_populates="patients")
    
    meal_plans = relationship("MealPlan", back_populates="patient")

class MealPlan(Base):
    __tablename__ = "meal_plans"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    meal_text = Column(Text) # Stores the JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    patient = relationship("Patient", back_populates="meal_plans")