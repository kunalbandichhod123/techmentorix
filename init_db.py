# init_db.py
from app.db import engine, Base
# ⚠️ IMPORT ALL MODELS HERE so SQLAlchemy knows about them
from app.models import User, Patient, MealPlan 

print("🔄 Connecting to Database...")
print(f"Targeting: {engine.url}")

def init_db():
    print("🛠️ Creating tables...")
    # This command looks at your imported models and creates tables if missing
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")

if __name__ == "__main__":
    init_db()