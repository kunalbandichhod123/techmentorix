import fitz  # PyMuPDF
import os
import re
import json

def clean_text(text: str) -> str:
    """
    Improved cleanup for RAG:
    - Normalizes horizontal spaces but PRESERVES newlines for lists/recipes.
    - Removes 'Page X' markers.
    - Removes non-printable characters.
    """
    # 1. Remove "Page X" or "Page | X" patterns
    text = re.sub(r"Page\s*\|?\s*\d+", "", text, flags=re.IGNORECASE)
    
    # 2. Remove non-printable/control characters (keep newlines \n)
    text = "".join(char for char in text if char.isprintable() or char == "\n")
    
    # 3. FIX: Only normalize horizontal spaces (don't merge everything into one line)
    # This keeps ingredients on separate lines as they appear in the PDF.
    text = re.sub(r"[ \t]+", " ", text)
    
    # 4. Normalize multiple newlines (max 2) to keep paragraph breaks but avoid huge gaps
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    
    return text.strip()


def extract_pdf_text(pdf_path):
    """
    Extracts text with intelligent 'Spread Detection' for 2-in-1 pages.
    Uses 'sort=True' and coordinate clipping to maintain logical reading order.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"❌ Failed to open {pdf_path}: {e}")
        return []

    data = []
    doc_id = os.path.basename(pdf_path).replace(".pdf", "")
    total_chars = 0

    for page_num, page in enumerate(doc, start=1):
        rect = page.rect
        width, height = rect.width, rect.height

        # LOGIC: If width > height, it's a '2-page-in-1' spread (common in Cookbooks)
        if width > height * 1.2:
            # Create two rectangles: Left Half and Right Half
            left_half = fitz.Rect(0, 0, width / 2, height)
            right_half = fitz.Rect(width / 2, 0, width, height)
            
            # Extract text from each half independently to avoid column mixing
            text_left = page.get_text("text", clip=left_half, sort=True)
            text_right = page.get_text("text", clip=right_half, sort=True)
            
            sections = [
                {"suffix": "L", "text": text_left},
                {"suffix": "R", "text": text_right}
            ]
        else:
            # Standard single page
            sections = [{"suffix": "", "text": page.get_text("text", sort=True)}]

        for section in sections:
            cleaned = clean_text(section["text"])
            if not cleaned:
                continue

            total_chars += len(cleaned)
            
            entry = {
                "id": f"{doc_id}_pg{page_num}{section['suffix']}",
                "doc_id": doc_id,
                "page": page_num,
                "text": cleaned
            }
            data.append(entry)

    doc.close()
    print(f"   📊 Summary: {len(data)} logical pages | {total_chars} chars.")
    return data


def process_pdfs(pdf_dir, out_dir):
    """
    Reads PDFs and saves JSONs. Skips existing files to save time.
    """
    if not os.path.exists(pdf_dir):
        print(f"❌ Error: Input directory '{pdf_dir}' not found.")
        return

    os.makedirs(out_dir, exist_ok=True)
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

    for fname in pdf_files:
        pdf_path = os.path.join(pdf_dir, fname)
        out_name = os.path.splitext(fname)[0] + ".json"
        out_path = os.path.join(out_dir, out_name)

        # SKIP logic: maintain efficiency
        if os.path.exists(out_path):
            print(f"⏩ Skipping (already exists): {fname}")
            continue

        print(f"📄 Processing: {fname}...")
        structured_data = extract_pdf_text(pdf_path)

        if structured_data:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved: {out_name}")


if __name__ == "__main__":
    process_pdfs(
        pdf_dir="../Data PDFs",
        out_dir="../ayurveda_texts_json"
    )