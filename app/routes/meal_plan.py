import os
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt

# --- REPORTLAB IMPORTS ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, Table, TableStyle, PageBreak, Image
)

# --- APP IMPORTS ---
from app.db import SessionLocal
from app.models import Patient, MealPlan, User
from app.services.groq_service import generate_meal_plan
from app.auth.jwt import SECRET_KEY, ALGORITHM

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/verify-otp")

# --- DIRECTORY CONFIGURATION ---
# We calculate the root based on where this file is located (app/routes/meal_plans.py)
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__)) # app/routes
APP_DIR = os.path.dirname(CURRENT_FILE_DIR) # app
BASE_DIR = os.path.dirname(APP_DIR) # project root

PDF_DIR = os.path.join(BASE_DIR, "generated_pdfs")
ASSETS_DIR = os.path.join(APP_DIR, "assets") # Expects: app/assets/

os.makedirs(PDF_DIR, exist_ok=True)

# ---------------- SCHEMAS ----------------
class MealUpdate(BaseModel):
    meal_text: str

class PatientClinicalData(BaseModel):
    agni: Optional[str] = None
    ama: Optional[str] = None
    roga: Optional[str] = None
    prakriti: Optional[str] = None
    disease: Optional[str] = None

# ---------------- DB & AUTH DEPENDENCIES ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone = payload.get("sub")
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==========================================================
# 🚀 ROUTE HANDLERS
# ==========================================================

@router.get("/{patient_id}/meal-plan")
def get_patient_meal_plan_history(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    meal_plan = db.query(MealPlan).filter(MealPlan.patient_id == patient_id).order_by(MealPlan.id.desc()).first()
    if not meal_plan:
        raise HTTPException(status_code=404, detail="No history found.")

    try:
        json.loads(meal_plan.meal_text)
        is_old = False
    except:
        is_old = True

    return {
        "id": patient_id,
        "meal_plan_id": meal_plan.id,
        "meal_text": meal_plan.meal_text,
        "is_old_format": is_old
    }

@router.post("/{patient_id}/meal-plan")
def generate_patient_meal_plan(
    patient_id: int,
    request_data: PatientClinicalData,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient or (user.role == "doctor" and patient.doctor_id != user.id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    if request_data.agni: patient.agni = request_data.agni
    if request_data.ama: patient.ama = request_data.ama
    if request_data.roga: patient.roga = request_data.roga
    if request_data.prakriti: patient.prakriti = request_data.prakriti
    if request_data.disease: patient.disease = request_data.disease
    
    db.commit()
    db.refresh(patient)

    meal_text = generate_meal_plan({
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "prakriti": patient.prakriti,
        "vikriti": patient.disease,
        "agni": patient.agni,
        "ama": patient.ama,
        "roga": patient.roga
    })

    try:
        json.loads(meal_text)
    except:
        raise HTTPException(status_code=500, detail="AI Error: Invalid JSON format")

    meal_plan = db.query(MealPlan).filter(MealPlan.patient_id == patient_id).first()
    if not meal_plan:
        meal_plan = MealPlan(patient_id=patient.id, meal_text=meal_text)
        db.add(meal_plan)
    else:
        meal_plan.meal_text = meal_text

    db.commit()
    db.refresh(meal_plan)
    
    save_meal_plan_pdf(meal_text, meal_plan.id)

    return {"id": patient.id, "meal_plan_id": meal_plan.id, "meal_text": meal_plan.meal_text}

@router.put("/{patient_id}/meal-plan")
def update_meal_plan(patient_id: int, data: MealUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meal_plan = db.query(MealPlan).filter(MealPlan.patient_id == patient_id).first()
    if not meal_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    meal_plan.meal_text = data.meal_text
    db.commit()
    
    save_meal_plan_pdf(data.meal_text, meal_plan.id)
    return {"message": "Success"}

# --- UPDATED DOWNLOAD ROUTE ---
@router.get("/pdf/{meal_plan_id}")
def download_meal_plan_pdf(meal_plan_id: int, db: Session = Depends(get_db)):
    meal_plan = db.query(MealPlan).filter(MealPlan.id == meal_plan_id).first()
    if not meal_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Force Regeneration
    save_meal_plan_pdf(meal_plan.meal_text, meal_plan.id)
    
    file_path = os.path.join(PDF_DIR, f"meal_plan_{meal_plan_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    # Add timestamp to filename to prevent browser caching
    timestamp = datetime.now().strftime("%H%M%S")
    download_name = f"Aarogyam_Plan_{meal_plan_id}_{timestamp}.pdf"

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    
    return FileResponse(
        path=file_path, 
        filename=download_name, 
        media_type='application/pdf',
        headers=headers
    )


# ==========================================================
# 🎨 HIGH-FIDELITY PDF ENGINE (Image-Based)
# ==========================================================

def save_meal_plan_pdf(json_text: str, meal_plan_id: int):
    # --- 1. Fetch Patient Data ---
    db = SessionLocal()
    patient_info = {}
    
    try:
        plan = db.query(MealPlan).filter(MealPlan.id == meal_plan_id).first()
        if plan:
            patient = db.query(Patient).filter(Patient.id == plan.patient_id).first()
            if patient:
                plan_date = plan.created_at.strftime('%d-%b-%Y')
                def clean(val):
                    return str(val) if val and str(val).lower() != 'none' else "-"
                patient_info = {
                    "name": patient.name,
                    "id": f"P-{patient.id:04d}",
                    "date": plan_date,
                    "age": f"{patient.age} Yrs",
                    "gender": patient.gender,
                    "height": f"{patient.height} cm" if patient.height else "-",
                    "weight": f"{patient.weight} kg" if patient.weight else "-",
                    "prakriti": clean(patient.prakriti),
                    "vikriti": clean(patient.disease), 
                    "agni": clean(getattr(patient, 'agni', '-')), 
                    "ama": clean(getattr(patient, 'ama', '-')),
                    "roga": clean(getattr(patient, 'roga', '-')) 
                }
    except Exception as e:
        print(f"⚠️ PDF DB Error: {e}")
    finally:
        db.close()

    try:
        data = json.loads(json_text)
    except:
        return 

    # --- 2. ASSET CHECK ---
    print(f"\n🔍 CHECKING ASSETS IN: {ASSETS_DIR}")
    bg_page1 = os.path.join(ASSETS_DIR, "background_page1.jpg")
    logo_img = os.path.join(ASSETS_DIR, "logo.png")
    vata_img = os.path.join(ASSETS_DIR, "vata_man.png")
    pitta_img = os.path.join(ASSETS_DIR, "pitta_man.png")
    kapha_img = os.path.join(ASSETS_DIR, "kapha_man.png")

    if os.path.exists(bg_page1): print("✅ Found Background") 
    else: print(f"❌ MISSING Background at: {bg_page1}")

    if os.path.exists(logo_img): print("✅ Found Logo") 
    else: print(f"❌ MISSING Logo at: {logo_img}")

    # --- 3. COLORS & STYLES ---
    theme_green = colors.HexColor("#1B4D3E")      
    theme_gold = colors.HexColor("#C5A065")       
    theme_beige = colors.HexColor("#FCFAF5")   
    theme_text = colors.HexColor("#2F2F2F")
    theme_light_gold = colors.HexColor("#EEDCBA")
    
    file_path = os.path.join(PDF_DIR, f"meal_plan_{meal_plan_id}.pdf")
    
    # --- 4. Background Layouts ---
    def draw_background_page1(canvas, doc):
        canvas.saveState()
        w, h = A4
        
        # 1. Background Image
        if os.path.exists(bg_page1):
             canvas.drawImage(bg_page1, 0, 0, width=w, height=h)
        else:
             # FALLBACK MODE (If image is missing)
             canvas.setStrokeColor(theme_gold)
             canvas.setLineWidth(2)
             canvas.rect(10*mm, 10*mm, w-20*mm, h-20*mm)

        # 2. Logo
        if os.path.exists(logo_img):
            canvas.drawImage(logo_img, w/2 - 40, h - 110, width=80, height=60, mask='auto')

        # 3. Title
        canvas.setFillColor(theme_text)
        canvas.setFont("Helvetica-Bold", 24)
        canvas.drawCentredString(w/2, h - 140, "Ayurvedic Clinical Assessment & Profile")
        
        # 4. Footer (Page Name & Date)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(15*mm, 15*mm, "Aarogyam")
        canvas.drawRightString(w-15*mm, 15*mm, f"Date: {patient_info.get('date','-')}")

        canvas.restoreState()

    def draw_background_other_pages(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setStrokeColor(theme_gold)
        canvas.setLineWidth(1)
        canvas.rect(10*mm, 10*mm, w-20*mm, h-20*mm)

        header_height = 28*mm
        canvas.setFillColor(theme_green)
        canvas.rect(10*mm, h - header_height - 10*mm, w-20*mm, header_height, fill=1, stroke=0)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawCentredString(w/2, h - 22*mm, "AAROGYAM")

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(theme_gold)
        canvas.drawCentredString(w/2, h - 30*mm, "INTEGRATIVE AYURVEDIC NUTRITION")

        # Footer (Page Name & Date)
        canvas.setFillColor(theme_text)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(15*mm, 15*mm, "Aarogyam")
        canvas.drawRightString(w-15*mm, 15*mm, f"Date: {patient_info.get('date','-')}")
        canvas.restoreState()

    styles = getSampleStyleSheet()
    style_label = ParagraphStyle('Label', parent=styles['Normal'], fontSize=10, textColor=theme_text, leading=14)
    style_value = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10, textColor=theme_text, fontName='Helvetica-Bold', leading=14)
    style_section_title = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=14, textColor=theme_green, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=10)
    style_day_header = ParagraphStyle('DayHeader', parent=styles['Heading3'], fontSize=14, textColor=theme_green, fontName='Helvetica-Bold', alignment=TA_CENTER)

    def create_info_box(title, content_data):
        title_para = Paragraph(title, style_section_title)
        t_content = Table(content_data, colWidths=[1.5*inch, 2.0*inch])
        t_content.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, theme_light_gold),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        t_box = Table([[title_para], [t_content]], colWidths=[3.7*inch])
        t_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), theme_beige),
            ('BOX', (0,0), (-1,-1), 1, theme_gold),
            ('TOPPADDING', (0,0), (0,0), 10),
            ('BOTTOMPADDING', (0,1), (0,1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        return t_box

    elements = []
    
    # === PAGE 1 ===
    elements.append(Spacer(1, 2.0*inch))

    demo_data = [
        [Paragraph("Name", style_label), Paragraph(patient_info['name'], style_value)],
        [Paragraph("Patient Number", style_label), Paragraph(patient_info['id'], style_value)],
        [Paragraph("Date", style_label), Paragraph(patient_info['date'], style_value)],
        [Paragraph("Age / Gender", style_label), Paragraph(f"{patient_info['age']} / {patient_info['gender']}", style_value)],
    ]
    box_demographics = create_info_box("Patient Demographics", demo_data)

    clinical_data = [
        [Paragraph("Height", style_label), Paragraph(patient_info['height'], style_value)],
        [Paragraph("Weight", style_label), Paragraph(patient_info['weight'], style_value)],
        [Paragraph("Agni (Digestion)", style_label), Paragraph(patient_info['agni'], style_value)],
        [Paragraph("Ama (Toxins)", style_label), Paragraph(patient_info['ama'], style_value)],
    ]
    box_clinical = create_info_box("Clinical History & Vitals", clinical_data)

    notes_data = [
        [Paragraph("Diagnosis", style_label), Paragraph(patient_info['vikriti'], style_value)],
        [Paragraph("Roga (Condition)", style_label), Paragraph(patient_info['roga'], style_value)],
    ]
    box_notes = create_info_box("Doctor's Notes / Samprapti", notes_data)
    
    left_column_stack = [box_demographics, Spacer(1, 0.2*inch), box_clinical, Spacer(1, 0.2*inch), box_notes]

    def get_dosha_block(img_path, dosha_name):
        if os.path.exists(img_path):
             img = Image(img_path, width=0.8*inch, height=1.8*inch) 
        else:
             img = Spacer(0.8*inch, 1.8*inch)
        text = Paragraph(f"<b>{dosha_name}</b>", style_value)
        return Table([[img], [text]], colWidths=[0.8*inch], style=[('ALIGN', (0,0), (-1,-1), 'CENTER')])

    vata_block = get_dosha_block(vata_img, "Vata")
    pitta_block = get_dosha_block(pitta_img, "Pitta")
    kapha_block = get_dosha_block(kapha_img, "Kapha")

    dosha_row = Table([[vata_block, pitta_block, kapha_block]], colWidths=[1.2*inch, 1.2*inch, 1.2*inch])
    dosha_row.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))

    diagnosis_text = Paragraph(f"<b>Diagnosis:</b><br/>Prakriti: {patient_info['prakriti']}<br/>Vikriti: {patient_info['vikriti']}", style_section_title)

    t_profile_content = Table([
        [Paragraph("Ayurvedic Profile", style_section_title)],
        [dosha_row],
        [Spacer(1, 0.2*inch)],
        [diagnosis_text]
    ], colWidths=[3.7*inch])
    
    t_profile_box = Table([[t_profile_content]], colWidths=[3.9*inch])
    t_profile_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), theme_beige),
        ('BOX', (0,0), (-1,-1), 1, theme_gold),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))

    t_main_layout = Table([
        [Table([[item] for item in left_column_stack]), t_profile_box]
    ], colWidths=[3.9*inch, 4.1*inch])
    
    t_main_layout.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))

    elements.append(t_main_layout)
    elements.append(PageBreak())

    # === PAGE 2+ (DIET) ===
    day_items = list(data.items())
    for i, (day, info) in enumerate(day_items):
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"{day}", style_day_header))
        elements.append(Spacer(1, 0.1*inch))
        
        if "meals" in info:
            rows = [[Paragraph("TIME", style_label), Paragraph("RECOMMENDED MEAL", style_label), Paragraph("CAL", style_label)]]
            for m in info["meals"]:
                menu_text = f"<b>{m.get('opt1','')}</b>"
                if m.get('opt2') and m.get('opt2') not in ['-', '']:
                    menu_text += f"<br/><font size=9 color='#666666'>OR {m.get('opt2','')}</font>"
                rows.append([
                    Paragraph(f"<b>{m.get('meal', '').upper()}</b>", style_value),
                    Paragraph(menu_text, style_value), 
                    Paragraph(m.get("cal1", ""), style_label)
                ])
            t_meals = Table(rows, colWidths=[1.0*inch, 5.0*inch, 1.0*inch], hAlign='CENTER')
            t_meals.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), theme_green), 
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),
                ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
                ('BACKGROUND', (0,1), (-1,-1), theme_beige), 
                ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(t_meals)
            elements.append(Spacer(1, 0.2*inch))

        w_list = info.get("workout", [])
        w_text = ", ".join(w_list) if isinstance(w_list, list) else str(w_list)
        l_text = info.get("lifestyle", "")
        r = info.get("recipe", {})
        r_text = f"<b>{r.get('name','Recipe')}</b>: {r.get('ins','')}" if isinstance(r, dict) else ""

        def create_simple_box(title, content):
             return Table([[Paragraph(title, style_section_title)], [Paragraph(content, style_label)]], 
                          colWidths=[7*inch],
                          style=[('BOX', (0,0), (-1,-1), 0.5, theme_green), ('BACKGROUND', (0,0), (-1,-1), theme_beige), ('PADDING', (0,0), (-1,-1), 6)])

        elements.append(create_simple_box("Yoga / Activity", w_text))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(create_simple_box("Lifestyle Tip", l_text))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(create_simple_box("Recipe", r_text))

        if (i + 1) % 2 == 0:
            elements.append(PageBreak())
        else:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("<hr width='50%' color='#C5A065'/>", styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))

    doc = BaseDocTemplate(file_path, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm)
    frame_p1 = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='p1')
    frame_other = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='other')
    template_p1 = PageTemplate(id='page1', frames=frame_p1, onPage=draw_background_page1)
    template_other = PageTemplate(id='others', frames=frame_other, onPage=draw_background_other_pages)
    doc.addPageTemplates([template_p1, template_other])
    
    print(f"✅ PDF Generated Successfully at: {file_path}")
    doc.build(elements)