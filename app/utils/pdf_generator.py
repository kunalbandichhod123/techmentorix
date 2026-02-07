from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import os

PDF_DIR = "generated_pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

def generate_meal_plan_pdf(meal_text: str, meal_plan_id: int):
    pdf_path = f"{PDF_DIR}/meal_plan_{meal_plan_id}.pdf"

    # Convert text to table rows
    rows = [
        [cell.strip() for cell in line.split("|")]
        for line in meal_text.split("\n")
        if "|" in line
    ]

    if len(rows) < 2:
        raise ValueError("Invalid meal plan format")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    table = Table(rows, repeatRows=1)

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    doc.build([table])
