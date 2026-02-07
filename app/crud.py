from sqlalchemy.orm import Session
from app import models, schemas

def create_patient(db: Session, patient: schemas.PatientCreate):
    new_patient = models.Patient(
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        height=patient.height,
        weight=patient.weight,
        disease=patient.disease,
        prakriti=patient.prakriti
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return new_patient


def create_meal_plan(db: Session, patient_id: int, meal_text: str):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()

    if not patient:
        return None

    meal_plan = models.MealPlan(
        meal_text=meal_text,
        patient_id=patient_id
    )

    db.add(meal_plan)
    db.commit()
    db.refresh(meal_plan)

    return meal_plan


def get_meal_plan(db: Session, meal_plan_id: int):
    return db.query(models.MealPlan).filter(models.MealPlan.id == meal_plan_id).first()
