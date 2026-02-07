# chunk_texts.py  — Ayurveda RAG Chunker (Advanced, Clean, Production Ready)

import os
import json
import argparse
import re
import hashlib
import nltk  # Added this for the auto-fix
from tqdm import tqdm

# --- BOOTSTRAP: Automatic NLTK Setup ---
def setup_nltk():
    """Ensures necessary NLTK data is downloaded once."""
    try:
        nltk.data.find('tokenizers/punkt')
    except (LookupError, AttributeError):
        print("📥 First-time setup: Downloading sentence tokenizer data...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)

setup_nltk()
# --------------------------------------

from nltk.tokenize import sent_tokenize # Import this AFTER setup
# ---------------- CONFIG ----------------
MAX_WORDS = 150
OVERLAP_WORDS = 80
CONSOLIDATED = "../chunks_meta.jsonl"
JSON_DIR_DEFAULT = "../ayurveda_texts_json"
OUT_DIR_DEFAULT = "../chunks"
# --------------------------------------

# ---------------- Utility ----------------

def words_count(s: str) -> int:
    return len(s.split())


def sha256_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------- Core Chunking ----------------

def chunk_text(text: str, max_words=MAX_WORDS, overlap_words=OVERLAP_WORDS):
    """
    Split text into semantic chunks using sentence boundaries with overlap.
    Original logic preserved.
    """
    sentences = sent_tokenize(text)
    chunks, cur_sentences, cur_words = [], [], 0

    for sent in sentences:
        w = words_count(sent)

        if cur_words + w <= max_words:
            cur_sentences.append(sent)
            cur_words += w
        else:
            if cur_sentences:
                chunks.append(" ".join(cur_sentences))

            if overlap_words > 0:
                overlap, ov_count = [], 0
                while cur_sentences and ov_count < overlap_words:
                    s = cur_sentences.pop()
                    overlap.insert(0, s)
                    ov_count += words_count(s)
                cur_sentences, cur_words = overlap, ov_count
            else:
                cur_sentences, cur_words = [], 0

            cur_sentences.append(sent)
            cur_words += w

    if cur_sentences:
        chunks.append(" ".join(cur_sentences))

    return chunks


def chunk_by_headings_and_paragraphs(text: str):
    """
    Advanced Ayurveda-aware chunking.
    Preserves meaningful blocks like Nidana, Lakshana, Chikitsa, Pathya, etc.
    Falls back to sentence chunking if block is too large.
    """

    ayurveda_headings = [
        # Classical structure
        "Nidana", "Hetu", "Purvarupa", "Rupa", "Samprapti", "Lakshana", "Chikitsa",
        "Pathya", "Apathya", "Upashaya", "Anupashaya",

        # Dosha concepts
        "Vata", "Pitta", "Kapha", "Tridosha", "Dosha", "Prakriti", "Vikriti",

        # Dietetics
        "Ahara", "Vihara", "Bhojana", "Anna", "Peya", "Yusha", "Kadha", "Kwath",
        "Ghrita", "Taila", "Lepa", "Asava", "Arishta", "Churna",

        # Rasa & properties
        "Rasa", "Guna", "Virya", "Vipaka", "Prabhava",

        # Lifestyle
        "Dinacharya", "Ritucharya", "Sadvritta", "Achar Rasayana",

        # Yoga
        "Yoga", "Asana", "Pranayama", "Dhyana", "Meditation", "Bandha", "Mudra", "Exercises", "Workouts",

        # Diseases
        "Jwara", "Atisara", "Grahani", "Arsha", "Kasa", "Shwasa", "Prameha", "Amlapitta",

        # General
        "Introduction", "Overview", "Conclusion", "Summary", "Indications", "Contraindications"
    ]

    # Split by paragraph blocks
    paras = re.split(r"\n\s*\n", text.strip())
    final_chunks = []

    heading_pattern = r"^\s*(" + "|".join([re.escape(h) for h in ayurveda_headings]) + r")\b"

    for para in paras:
        para = para.strip()
        if not para:
            continue

        # If paragraph starts with Ayurveda heading, keep as a block
        if re.match(heading_pattern, para, re.IGNORECASE):
            if words_count(para) > MAX_WORDS:
                final_chunks.extend(chunk_text(para))
            else:
                final_chunks.append(para)
        else:
            # Normal paragraph
            if words_count(para) > MAX_WORDS:
                final_chunks.extend(chunk_text(para))
            else:
                final_chunks.append(para)

    return [c for c in final_chunks if c.strip()]


# ---------------- Main Processing ----------------

def process_all(json_dir=JSON_DIR_DEFAULT, out_dir=OUT_DIR_DEFAULT, consolidated=CONSOLIDATED):
    """
    Reads extracted text JSON files and creates chunked files + consolidated JSONL.
    Skips already processed documents safely.
    """

    os.makedirs(out_dir, exist_ok=True)
    already_done = set()

    if os.path.exists(consolidated):
        with open(consolidated, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    meta = json.loads(line)
                    already_done.add(meta["doc_id"])
                except:
                    continue

    with open(consolidated, "a", encoding="utf-8") as cons_f:
        for fname in tqdm(sorted(os.listdir(json_dir)), desc="Processing PDFs"):
            if not fname.lower().endswith(".json"):
                continue

            doc_id = os.path.splitext(fname)[0]

            if doc_id in already_done:
                print(f"⏩ Skipping {fname}, already processed.")
                continue

            path = os.path.join(json_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                pages = json.load(f)

            file_chunks_meta = []

            for page in pages:
                page_text = page.get("text", "").strip()
                if not page_text:
                    continue

                # Advanced paragraph + heading chunking
                para_chunks = chunk_by_headings_and_paragraphs(page_text)

                all_chunks = []
                for pc in para_chunks:
                    if words_count(pc) > MAX_WORDS:
                        all_chunks.extend(chunk_text(pc))
                    else:
                        all_chunks.append(pc)

                for i, ch in enumerate(all_chunks):
                    chunk_id = f"{doc_id}__p{page.get('page', 0)}__c{i}"

                    meta = {
                        "id": chunk_id,
                        "doc_id": doc_id,
                        "page": page.get("page", None),
                        "text": ch.strip(),
                        "word_count": words_count(ch),
                        "hash": sha256_of_text(ch)
                    }

                    file_chunks_meta.append(meta)
                    cons_f.write(json.dumps(meta, ensure_ascii=False) + "\n")

            out_file = os.path.join(out_dir, fname)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(file_chunks_meta, f, ensure_ascii=False, indent=2)

            print(f"✅ Processed {fname}, chunks saved.")

    print(f"All done — chunks appended to '{consolidated}'")


def create_chunks(input_folder=JSON_DIR_DEFAULT, output_file=CONSOLIDATED):
    process_all(json_dir=input_folder, consolidated=output_file)
    print(f"✅ Chunk creation complete: {output_file}")


# ---------------- CLI ----------------

def main():
    # 1. Use the paths from your CONFIG
    json_dir = JSON_DIR_DEFAULT 
    out_dir = OUT_DIR_DEFAULT
    consolidated_path = CONSOLIDATED

    # 2. Ensure the chunks folder is created in the MAIN directory
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        print(f"📁 Created directory: {out_dir}")

    print(f"🔍 Looking for JSON files in: {json_dir}")

    # 3. Call process_all with the 3 names it expects
    process_all(
        json_dir=json_dir,
        out_dir=out_dir,
        consolidated=consolidated_path
    )

if __name__ == "__main__":
    main()