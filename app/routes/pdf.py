# app/routes/pdf.py
import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

# --- REPORTLAB IMPORTS ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, 
    Spacer, Table, TableStyle, PageBreak, KeepTogether
)

from app.db import SessionLocal
from app.models import MealPlan, Patient

router = APIRouter(
    tags=["PDF"]
)

# --- DIRECTORY CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "generated_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================================
# 🎨 HIGH-FIDELITY PDF GENERATOR ENGINE
# ==========================================================
def generate_enhanced_pdf(filepath: str, meal_text: str, patient: Patient):
    """
    Generates a professional multi-page PDF.
    Page 1: Patient Profile & Doctor Inputs.
    Page 2+: Meal Plan (2 days per page) + Workouts/Tips/Recipes.
    """
    
    # --- 1. Colors & Styles ---
    theme_green = colors.HexColor("#1B4D3E")  # Dark Green Header
    theme_gold = colors.HexColor("#C5A065")   # Gold Accents
    theme_beige = colors.HexColor("#F5F0E6")  # Backgrounds
    theme_text = colors.HexColor("#2F2F2F")   # Dark Grey Text
    
    styles = getSampleStyleSheet()
    style_label = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=theme_text, leading=12)
    style_value = ParagraphStyle('Value', parent=styles['Normal'], fontSize=9, textColor=theme_text, fontName='Helvetica-Bold', leading=12)
    style_header = ParagraphStyle('Header', parent=styles['Normal'], fontSize=16, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    style_sub = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=theme_gold, alignment=TA_CENTER)
    style_day = ParagraphStyle('Day', parent=styles['Heading3'], fontSize=14, textColor=theme_green, fontName='Helvetica-Bold', alignment=TA_CENTER)
    
    # --- 2. Helper: Create Styled Box ---
    def create_box(title, content_rows):
        # Title Row
        data = [[Paragraph(f"<b>{title}</b>", style_value)]]
        # Content Rows
        for row in content_rows:
            data.append(row)
        
        t = Table(data, colWidths=[7.0*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), theme_beige), # Title Background
            ('TEXTCOLOR', (0,0), (-1,0), theme_green),
            ('BOX', (0,0), (-1,-1), 0.5, theme_green),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    # --- 3. Background (Header & Footer) ---
    def draw_background(canvas, doc):
        canvas.saveState()
        w, h = A4
        
        # Border
        canvas.setStrokeColor(theme_gold)
        canvas.setLineWidth(1)
        canvas.rect(10*mm, 10*mm, w-20*mm, h-20*mm) 
        
        # Header Block
        header_height = 25*mm 
        canvas.setFillColor(theme_green)
        canvas.rect(10*mm, h - header_height - 10*mm, w-20*mm, header_height, fill=1, stroke=0)

        # Header Text
        canvas.setFont("Helvetica-Bold", 16)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(w/2, h - 20*mm, "Aarogyam")
        
        canvas.setFont("Helvetica", 10)
        canvas.setFillColor(theme_gold)
        canvas.drawCentredString(w/2, h - 26*mm, "Personalized Diet & Lifestyle Plan")

        # Footer
        canvas.setFillColor(theme_text)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(15*mm, 15*mm, "Prescribed by: Dr. V. Sharma, BAMS")
        canvas.drawRightString(w-15*mm, 15*mm, f"Patient: {patient.name} | Page {doc.page}")

        canvas.restoreState()

    # --- 4. Build Content Elements ---
    elements = []
    
    # === PAGE 1: PATIENT PROFILE ===
    elements.append(Spacer(1, 1.2*inch)) # Space for Header

    # Patient Vitals Table
    vitals_data = [
        [Paragraph(f"Name: {patient.name}", style_value), Paragraph(f"ID: P-{patient.id}", style_label)],
        [Paragraph(f"Age: {patient.age}", style_label), Paragraph(f"Gender: {patient.gender}", style_label)],
        [Paragraph(f"Height: {patient.height or '-'} cm", style_label), Paragraph(f"Weight: {patient.weight or '-'} kg", style_label)],
    ]
    t_vitals = Table(vitals_data, colWidths=[3.5*inch, 3.5*inch])
    t_vitals.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    
    elements.append(create_box("Patient Vitals", [[t_vitals]]))
    elements.append(Spacer(1, 0.2*inch))

    # Ayurvedic Assessment (Safe Getters)
    prakriti = patient.prakriti or "-"
    disease = patient.disease or "-"
    # Note: Ensure your Patient model has these fields or use placeholders
    agni = getattr(patient, 'agni', '-')
    ama = getattr(patient, 'ama', '-')

    ayur_data = [
        [Paragraph(f"<b>Prakriti:</b> {prakriti}", style_label), Paragraph(f"<b>Vikriti/Disease:</b> {disease}", style_label)],
        [Paragraph(f"<b>Agni:</b> {agni}", style_label), Paragraph(f"<b>Ama:</b> {ama}", style_label)],
    ]
    t_ayur = Table(ayur_data, colWidths=[3.5*inch, 3.5*inch])
    elements.append(create_box("Clinical Assessment", [[t_ayur]]))
    elements.append(Spacer(1, 0.2*inch))

    # Guidelines
    guidelines = [
        "• Drink warm water throughout the day.",
        "• Eat only when the previous meal is fully digested.",
        "• Avoid cold, heavy, and oily foods.",
        "• Dinner should be light and taken before 8 PM."
    ]
    g_rows = [[Paragraph(g, style_label)] for g in guidelines]
    elements.append(create_box("General Guidelines", g_rows))
    
    elements.append(PageBreak()) # End of Page 1


    # === PAGE 2+: MEAL PLAN ===
    try:
        plan_data = json.loads(meal_text)
    except:
        plan_data = {}

    day_items = list(plan_data.items())
    
    for i, (day, info) in enumerate(day_items):
        
        # Day Header
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"{day}", style_day))
        elements.append(Spacer(1, 0.1*inch))
        
        # 1. Meals Table
        if "meals" in info:
            # Header Row
            rows = [[
                Paragraph("<b>Time</b>", style_value), 
                Paragraph("<b>Menu Option 1</b>", style_value), 
                Paragraph("<b>Cal</b>", style_value),
                Paragraph("<b>Menu Option 2</b>", style_value),
                Paragraph("<b>Cal</b>", style_value)
            ]]
            
            for m in info["meals"]:
                rows.append([
                    Paragraph(m.get("meal", ""), style_value),
                    Paragraph(m.get("opt1", ""), style_label),
                    Paragraph(str(m.get("cal1", "")), style_label),
                    Paragraph(m.get("opt2", "-"), style_label),
                    Paragraph(str(m.get("cal2", "")), style_label),
                ])
            
            # Widths: Time, Opt1, Cal1, Opt2, Cal2
            t_meals = Table(rows, colWidths=[0.8*inch, 2.4*inch, 0.6*inch, 2.4*inch, 0.6*inch])
            t_meals.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), theme_beige),
                ('LINEBELOW', (0,0), (-1,0), 1, theme_green),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(t_meals)
            elements.append(Spacer(1, 0.15*inch))

        # 2. Extras (Workout, Tips, Recipe)
        extras_content = []
        
        # Workout
        w = info.get("workout", [])
        w_text = ", ".join(w) if isinstance(w, list) else str(w)
        extras_content.append([Paragraph(f"<b>🏃 Workout:</b> {w_text}", style_label)])
        
        # Tips
        l = info.get("lifestyle", "")
        extras_content.append([Paragraph(f"<b>🌿 Tip:</b> {l}", style_label)])
        
        # Recipe
        r = info.get("recipe", {})
        if isinstance(r, dict):
            r_text = f"<b>🍲 Recipe ({r.get('name','')}):</b> {r.get('ins','')}"
            extras_content.append([Paragraph(r_text, style_label)])
            
        t_extras = Table(extras_content, colWidths=[6.8*inch])
        t_extras.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, theme_green),
            ('BACKGROUND', (0,0), (-1,-1), theme_beige),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t_extras)

        # Logic: 2 Days per Page
        # If (i+1) is even (2, 4, 6...), insert PageBreak. Else, insert Separator.
        if (i + 1) % 2 == 0:
            elements.append(PageBreak())
        else:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<hr width='80%' color='#C5A065'/>", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

    # --- 5. BUILD PDF ---
    doc = BaseDocTemplate(filepath, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm)
    frame = Frame(10*mm, 10*mm, A4[0]-20*mm, A4[1]-35*mm, id='normal') 
    template = PageTemplate(id='background', frames=frame, onPage=draw_background)
    doc.addPageTemplates([template])
    
    try:
        doc.build(elements)
        print(f"✅ Generated PDF at: {filepath}")
        return True
    except Exception as e:
        print(f"❌ PDF Build Error: {e}")
        return False

# ==========================================================
# 🚀 API ROUTES
# ==========================================================
@router.get("/{meal_plan_id}")
def download_pdf_by_meal_plan(meal_plan_id: int, db: Session = Depends(get_db)):
    filename = f"meal_plan_{meal_plan_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, filename)

    # 1. Always delete old file to force regeneration
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    # 2. Fetch Data
    meal_plan = db.query(MealPlan).filter(MealPlan.id == meal_plan_id).first()
    if not meal_plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    
    patient = db.query(Patient).filter(Patient.id == meal_plan.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 3. Generate PDF (Passing full patient object now)
    success = generate_enhanced_pdf(pdf_path, meal_plan.meal_text, patient)

    if not success or not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)