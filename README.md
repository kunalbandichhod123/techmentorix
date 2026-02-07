# 🌿Aarogyam - TechMentorix

**AyurMeal** is a comprehensive Ayurvedic health management platform designed to bridge the gap between Ayurvedic doctors and patients. It features an intelligent meal planner, patient history tracking, and a secure authentication system for different user roles.

Here is a concise, high-impact To-Do list focusing on the critical milestones for your dashboards.

# ToDo List: AyurMeal Dashboards


* [x] **Repo & Env:** Git initialized, Virtual Environment setup
* [x] **Backend:** FastAPI setup, PostgreSQL connected
* [x] **Migrations:** Alembic sync (added Agni, Ama, Prakriti columns)
* [x] **Assets:** Images (`assets/`) added for PDF generation
* [x] **Sync:** Push latest code to GitHub

> **Doctor Dashboard (Priority)**

* [x] **Auth:** Email Login page (JWT integration)
* [x] **Patient List:** Table view of all registered patients
* [x] **Clinical Intake:** Form to input **Agni**, **Ama**, **Prakriti**, & **Vikriti**
* [x] **Generator UI:** Button to trigger Groq AI & preview JSON response
* [x] **PDF Action:** "Download Report" button (linked to new `/pdf/{id}` route)
* [x] **Enable RLS Security:** only patient can see his meal plan and doctor can see his patients

> **Patient Dashboard**

* [x] **Auth:** Patient Login (via Phone/OTP)
* [x] **Daily View:** Read-only display of Today's Meal Plan
* [x] **Profile:** Visual display of their Dosha (Vata/Pitta/Kapha)
* [x] **Downloads:** Access to their generated PDF report

> **AI & PDF Engine**

* [x] **Groq Integration:** AI prompt optimized for Ayurvedic logic
* [x] **PDF Design:** High-fidelity layout with borders & images
* [x] **Caching:** Fix implemented to force-regenerate PDFs on download
* [x] **Testing:** Verify end-to-end flow (Add Patient -> Generate -> Download)[https://github.com/kunalbandichhod123/techmentorix.git](https://github.com/kunalbandichhod123/techmentorix.git)
cd techmentorix
