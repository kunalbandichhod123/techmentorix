from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------------- PATIENT SCHEMAS ----------------

class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    height: int
    weight: int
    disease: Optional[str] = None
    prakriti: Optional[str] = None


class Patient(PatientCreate):
    id: int

    class Config:
        from_attributes = True


# ---------------- MEAL PLAN SCHEMAS ----------------

class MealPlanResponse(BaseModel):
    id: int
    meal_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class MealPlanUpdate(BaseModel):
    meal_text: str
