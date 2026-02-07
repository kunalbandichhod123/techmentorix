# hybrid_retrieval.py — Ayurveda Search Engine (Retrieval ONLY)

import os
import faiss
import json
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from whoosh import index
from whoosh.qparser import MultifieldParser

# ================= CONFIG =================
# These paths must match what you used in create_local_embeddings.py
FAISS_INDEX_FILE = "../faiss_index/index.faiss"
FAISS_METADATA_JSON = "../faiss_index/chunks.json"
FAISS_METADATA_PKL = "../faiss_index/faiss_metadata.pkl"
WHOOSH_INDEX_DIR = "../whoosh_index"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# =========================================

print("[INFO] Initializing Retrieval Engine...")

# Load Model once
embedder = SentenceTransformer(EMBEDDING_MODEL)

def load_faiss():
    """
    Loads FAISS index and metadata.
    Logic: Checks for a fast Pickle cache. If missing (because create_local_embeddings deleted it),
    it rebuilds it from the source JSON.
    """
    if not os.path.exists(FAISS_INDEX_FILE):
        raise FileNotFoundError(f"FAISS index missing at {FAISS_INDEX_FILE}. Run create_local_embeddings.py first.")

    # 1. Load the Vector Index
    index_faiss = faiss.read_index(FAISS_INDEX_FILE)

    # 2. Load the Metadata (Text)
    # If the Pickle exists, it is safe to use because create_local_embeddings deletes it on update.
    if os.path.exists(FAISS_METADATA_PKL):
        with open(FAISS_METADATA_PKL, "rb") as f:
            metadata = pickle.load(f)
    else:
        # Pickle is missing (fresh update), so load from JSON and save a new Pickle
        if not os.path.exists(FAISS_METADATA_JSON):
            raise FileNotFoundError(f"Metadata JSON missing at {FAISS_METADATA_JSON}")
            
        with open(FAISS_METADATA_JSON, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        with open(FAISS_METADATA_PKL, "wb") as f:
            pickle.dump(metadata, f)
        print("[INFO] Cache refreshed from source.")

    return index_faiss, metadata

def load_whoosh():
    """
    Opens the existing Whoosh index for keyword search.
    Read-Only mode.
    """
    if not os.path.exists(WHOOSH_INDEX_DIR):
        raise FileNotFoundError(f"Whoosh index missing at {WHOOSH_INDEX_DIR}. Run create_local_embeddings.py first.")
    
    return index.open_dir(WHOOSH_INDEX_DIR)

# --- GLOBAL LOAD (Happens once when script/app starts) ---
try:
    faiss_index, metadata = load_faiss()
    whoosh_index = load_whoosh()
    print(f"[OK] Search Engine Ready: {faiss_index.ntotal} vectors | {len(metadata)} docs")
except Exception as e:
    print(f"[ERROR] Could not load search engine: {e}")
    faiss_index, metadata, whoosh_index = None, [], None


def hybrid_search(query, top_k=8):
    """
    The main search function called by your Query Engine.
    Combines Vector Search (FAISS) + Keyword Search (Whoosh).
    """
    if not faiss_index or not whoosh_index:
        return []

    # 1. Semantic Search (FAISS)
    q_emb = embedder.encode(query, convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_emb.reshape(1, -1))

    safe_k = min(top_k, faiss_index.ntotal)
    _, I = faiss_index.search(q_emb.reshape(1, -1), safe_k)

    faiss_hits = []
    for idx in I[0]:
        if idx < len(metadata):
            faiss_hits.append(metadata[idx])

    # 2. Keyword Search (Whoosh)
    # We search specifically in the 'text' field
    parser = MultifieldParser(["text"], whoosh_index.schema)
    try:
        q = parser.parse(query)
    except:
        # Fallback if query contains special characters that break Whoosh
        q = None

    whoosh_hits = []
    if q:
        with whoosh_index.searcher() as searcher:
            # Get more than top_k to ensure good intersection
            for hit in searcher.search(q, limit=top_k*2): 
                whoosh_hits.append({"id": hit.get("id"), "text": hit.get("text")})

    # 3. Merge & Deduplicate
    # We use a dictionary keyed by the text itself to ensure no duplicates
    combined = {}
    
    # Priority 1: Keyword matches (often more specific)
    for c in whoosh_hits: 
        combined[c["text"]] = c
    
    # Priority 2: Semantic matches (fill in the context)
    for c in faiss_hits: 
        if c["text"] not in combined:
            combined[c["text"]] = c

    # Convert back to list and slice top_k
    results = list(combined.values())[:top_k]
    return results

if __name__ == "__main__":
    # Simple Test
    test_q = "Best foods for pitta dosha"
    print(f"\n🔎 Testing Search: '{test_q}'...")
    
    results = hybrid_search(test_q)
    
    if not results:
        print("No results found.")
    else:
        for i, res in enumerate(results, 1):
            print(f"{i}. {res['text'][:100]}...")