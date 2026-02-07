# app/routes/patients.py
import os
import json # needed for the update logic
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from groq import Groq 

from app.db import get_db
from app.models import MealPlan, Patient, User
from app.auth.auth import get_current_user

router = APIRouter()

# ---------------- SCHEMAS ----------------
class PatientCreate(BaseModel):
    name: str
    phone: str
    age: int
    gender: str
    height: Optional[int] = 0
    weight: Optional[int] = 0
    prakriti: Optional[str] = None
    vikriti: Optional[str] = None
    ama: Optional[str] = None
    roga: Optional[str] = None
    agni: Optional[str] = None
    doctor_notes: Optional[str] = None

class PatientOut(BaseModel):
    id: int
    name: str
    phone: str
    age: int
    gender: str
    prakriti: Optional[str]
    
    class Config:
        from_attributes = True

# 👇 NEW SCHEMA FOR SAVING EDITS
class MealPlanUpdate(BaseModel):
    meal_text: str

# ---------------- 1. CREATE PATIENT ----------------
@router.post("") 
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can add patients")

    existing = db.query(Patient).filter(Patient.phone == patient.phone).first()

    if existing:
        if existing.doctor_id != user.id:
            existing.doctor_id = user.id
            db.commit()
        return {"id": existing.id}

    new_patient = Patient(
        name=patient.name,
        phone=patient.phone,
        age=patient.age,
        gender=patient.gender,
        height=patient.height,
        weight=patient.weight,
        prakriti=patient.prakriti,
        disease=patient.roga, 
        doctor_id=user.id
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return {"id": new_patient.id}

# ---------------- 2. GENERATE MEAL PLAN (AI) ----------------
@router.post("/{patient_id}/meal-plan")
def create_patient_meal_plan(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can generate plans")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server AI Misconfiguration")
    
    client = Groq(api_key=api_key)

    # UPDATED PROMPT FOR STRICT JSON
    prompt = f"""
    You are an expert Ayurvedic Doctor. Create a 7-Day Vegetarian Meal Plan for:
    Name: {patient.name}, Age: {patient.age}, Gender: {patient.gender}
    Prakriti: {patient.prakriti or 'General'}
    
    IMPORTANT: Return the response as a RAW JSON OBJECT. Do not use Markdown formatting.
    Use exactly this structure for 7 days:
    {{
      "Day 1": {{
        "meals": [
          {{ "meal": "Breakfast", "opt1": "Food A", "cal1": "150 kcal", "opt2": "Food B", "cal2": "150 kcal" }},
          {{ "meal": "Lunch", "opt1": "Food A", "cal1": "400 kcal", "opt2": "Food B", "cal2": "400 kcal" }},
          {{ "meal": "Dinner", "opt1": "Food A", "cal1": "300 kcal", "opt2": "Food B", "cal2": "300 kcal" }}
        ],
        "workout": ["Yoga Move 1", "Exercise 2"],
        "lifestyle": "Daily ayurvedic tip",
        "recipe": {{ "name": "Dish Name", "ing": "Ingredients", "ins": "Instructions" }}
      }}
    }}
    Fill 7 days.
    """

    print("🤖 DEBUG: Sending request to AI...")

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7 
        )
        diet_text = chat_completion.choices[0].message.content
        # Cleanup Markdown if present
        diet_text = diet_text.replace("```json", "").replace("```", "").strip()
        print("✅ DEBUG: AI Response Received")
    except Exception as e:
        print(f"❌ AI ERROR: {e}")
        raise HTTPException(status_code=500, detail="AI Generation Failed")

    new_plan = MealPlan(patient_id=patient.id, meal_text=diet_text)
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)

    return {"meal_plan_id": new_plan.id, "meal_text": new_plan.meal_text}

# ---------------- 3. GET PATIENT MEAL PLAN ----------------
@router.get("/{patient_id}/meal-plan")
def get_patient_meal_plan(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view plans")

    plan = db.query(MealPlan).filter(MealPlan.patient_id == patient_id).order_by(MealPlan.created_at.desc()).first()

    if not plan:
        raise HTTPException(status_code=404, detail="No meal plan generated yet")

    return {"meal_plan_id": plan.id, "meal_text": plan.meal_text}

# ---------------- 4. UPDATE MEAL PLAN (✅ THIS FIXES THE 405 ERROR) ----------------
@router.put("/{patient_id}/meal-plan")
def update_patient_meal_plan(
    patient_id: int,
    plan_data: MealPlanUpdate, # Uses the new schema
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can edit plans")

    # Find the latest plan for this patient
    plan = db.query(MealPlan).filter(MealPlan.patient_id == patient_id).order_by(MealPlan.created_at.desc()).first()

    if not plan:
        raise HTTPException(status_code=404, detail="No meal plan found to update")

    # Update the text
    plan.meal_text = plan_data.meal_text
    db.commit()
    db.refresh(plan)

    return {"message": "Plan updated successfully", "meal_plan_id": plan.id}

# ---------------- 5. PATIENT HISTORY ----------------
@router.get("/history", response_model=List[PatientOut])
def get_previous_patients(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view history")

    return db.query(Patient).filter(Patient.doctor_id == user.id).order_by(Patient.id.desc()).all()

# ---------------- 6. DELETE PATIENT ----------------
@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can delete patients")

    db.query(MealPlan).filter(MealPlan.patient_id == patient_id).delete()
    db.query(Patient).filter(Patient.id == patient_id).delete()
    db.commit()
    return {"message": "Deleted successfully"}

# ---------------- 7. PATIENT PORTAL (MY PLAN) ----------------
@router.get("/my-plan")
def get_my_meal_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_phone = current_user.phone.strip()
    patient = db.query(Patient).filter(Patient.phone == user_phone).first()

    if not patient:
        alt_phone = user_phone.replace("+91", "") if "+91" in user_phone else f"+91{user_phone}"
        patient = db.query(Patient).filter(Patient.phone == alt_phone).first()

    if not patient:
        raise HTTPException(status_code=404, detail="No patient profile found.")

    meal_plan = db.query(MealPlan).filter(MealPlan.patient_id == patient.id).order_by(MealPlan.id.desc()).first()

    if not meal_plan:
        raise HTTPException(status_code=404, detail="No meal plan generated yet.")

    return {
        "meal_plan_id": meal_plan.id,
        "meal_text": meal_plan.meal_text,
        "created_at": meal_plan.created_at
    }