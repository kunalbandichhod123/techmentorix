# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# ---------------- ROUTER IMPORTS ----------------
# We import the routers we created in other files
from app.auth.auth import router as auth_router
from app.routes.patients import router as patients_router
from app.routes.pdf import router as pdf_router

# ⚠️ COMMENTED OUT: We moved the "my-plan" logic INSIDE patients.py.
# If you don't have a file named 'app/routes/meal_plan.py', this import would crash your app.
# from app.routes.meal_plan import router as meal_plan_router 

# Load environment variables
load_dotenv()

app = FastAPI()

# ---------------- CORS (MUST BE FIRST) ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ROUTER REGISTRATION ----------------
# 1. Auth routes (Login, OTP)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

# 2. Meal Plan Logic
# Since we added @router.get("/my-plan") inside 'patients.py', 
# the 'patients_router' handles this now. We don't need a separate meal_plan router.
# app.include_router(meal_plan_router, prefix="/patients", tags=["MealPlan"])

# 3. Patients Router (Handles /history, /my-plan, and / (create))
app.include_router(patients_router, prefix="/patients", tags=["Patients"])

# 4. PDF routes (For downloading the plan)
app.include_router(pdf_router, prefix="/pdf", tags=["PDF"])

# ---------------- STATIC FILES ----------------
# This allows the frontend to view the generated PDFs
app.mount(
    "/generated_pdfs",
    StaticFiles(directory="generated_pdfs"),
    name="generated_pdfs"
)

# ---------------- ROOT ----------------
@app.get("/")
def root():
    return {"status": "API running"}