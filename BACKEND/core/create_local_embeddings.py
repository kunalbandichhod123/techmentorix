# create_local_embeddings.py  (Ayurveda Assistant – Clean Embedding Pipeline)

import os
import json
import faiss
import numpy as np
import hashlib
import pickle
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from whoosh import index
from whoosh.fields import Schema, TEXT, ID

# -------- CONFIG ----------
MODEL_NAME = os.environ.get("EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
BATCH_SIZE = 32

OUT_DIR = "../faiss_index"
WHOOSH_INDEX_DIR = "../whoosh_index"
CHUNKS_META = "../chunks_meta.jsonl"   # input: chunk metadata lines

INDEX_FILE = os.path.join(OUT_DIR, "index.faiss")
META_FILE = os.path.join(OUT_DIR, "chunks.json")        # list of chunk metadata
ID_MAP_FILE = os.path.join(OUT_DIR, "id_to_index.json") # chunk_id -> faiss_id
SHA_FILE = os.path.join(OUT_DIR, "id_to_sha.json")      # chunk_id -> sha256
PKL_CACHE = os.path.join(OUT_DIR, "faiss_metadata.pkl") # Retrieval cache
# ---------------------------


def sha_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_existing_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as fh:
            saved_chunks = json.load(fh)
    else:
        saved_chunks = []

    if os.path.exists(ID_MAP_FILE):
        with open(ID_MAP_FILE, "r", encoding="utf-8") as fh:
            id_to_index = json.load(fh)
    else:
        id_to_index = {}

    if os.path.exists(SHA_FILE):
        with open(SHA_FILE, "r", encoding="utf-8") as fh:
            id_to_sha = json.load(fh)
    else:
        id_to_sha = {}

    return saved_chunks, id_to_index, id_to_sha


def read_all_chunks(input_path=CHUNKS_META):
    chunks = []
    if not os.path.exists(input_path):
        return []
    with open(input_path, "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                chunks.append(json.loads(line))
            except:
                continue
    return chunks


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Loading embedding model:", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    # Load existing state
    saved_chunks, id_to_index, id_to_sha = load_existing_meta()

    # Load all chunk entries
    all_chunks = read_all_chunks(CHUNKS_META)
    print(f"Total chunks in source file: {len(all_chunks)}")

    # Determine new or changed chunks
    new_chunks = []

    for c in all_chunks:
        cid = c.get("id")
        text = c.get("text", "")

        if not cid or not text:
            continue

        text_sha = sha_of_text(text)

        # Skip unchanged chunks
        if cid in id_to_sha and id_to_sha[cid] == text_sha:
            continue

        c["_sha"] = text_sha
        new_chunks.append(c)

    print(f"New or changed chunks to embed: {len(new_chunks)}")

    # Even if no NEW chunks for FAISS, we might need to verify Whoosh/Metadata
    if new_chunks:
        # Prepare FAISS index
        sample_emb = model.encode([new_chunks[0]["text"]], convert_to_numpy=True, show_progress_bar=False)
        dim = sample_emb.shape[1]

        if os.path.exists(INDEX_FILE):
            print("Loading existing FAISS index...")
            faiss_idx = faiss.read_index(INDEX_FILE)
            if not isinstance(faiss_idx, faiss.IndexIDMap):
                faiss_idx = faiss.IndexIDMap(faiss_idx)
        else:
            print("Creating new FAISS index...")
            base_index = faiss.IndexFlatIP(dim)
            faiss_idx = faiss.IndexIDMap(base_index)

        # Determine next FAISS ID
        used_ids = set(int(v) for v in id_to_index.values()) if id_to_index else set()
        next_faiss_id = (max(used_ids) + 1) if used_ids else 1

        # Encode in batches
        texts = [c["text"] for c in new_chunks]
        emb_list = []

        print("Encoding chunks in batches...")
        for i in tqdm(range(0, len(texts), BATCH_SIZE)):
            batch = texts[i:i + BATCH_SIZE]
            emb = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
            emb_list.append(emb)

        all_embs = np.vstack(emb_list).astype("float32")
        faiss.normalize_L2(all_embs)

        # Add to index
        print("Adding embeddings to FAISS index...")
        for emb_vec, chunk in zip(all_embs, new_chunks):
            f_id = next_faiss_id
            faiss_idx.add_with_ids(emb_vec.reshape(1, -1), np.array([f_id], dtype=np.int64))

            cid = chunk["id"]
            id_to_index[cid] = f_id
            id_to_sha[cid] = chunk["_sha"]
            saved_chunks.append(chunk)
            next_faiss_id += 1

        # Persist FAISS and Meta JSONs
        print("Saving FAISS index and metadata...")
        faiss.write_index(faiss_idx, INDEX_FILE)

        with open(META_FILE, "w", encoding="utf-8") as fh:
            json.dump(saved_chunks, fh, ensure_ascii=False, indent=2)

        id_to_index = {k: int(v) for k, v in id_to_index.items()}
        with open(ID_MAP_FILE, "w", encoding="utf-8") as fh:
            json.dump(id_to_index, fh, ensure_ascii=False, indent=2)

        with open(SHA_FILE, "w", encoding="utf-8") as fh:
            json.dump(id_to_sha, fh, ensure_ascii=False, indent=2)

    # --- WHOOSH INDEXING (KEYWORD SEARCH) ---
    print("[INFO] Updating Whoosh keyword index...")
    if not os.path.exists(WHOOSH_INDEX_DIR):
        os.makedirs(WHOOSH_INDEX_DIR)
        schema = Schema(id=ID(stored=True, unique=True), text=TEXT(stored=True))
        ix = index.create_in(WHOOSH_INDEX_DIR, schema)
    else:
        ix = index.open_dir(WHOOSH_INDEX_DIR)

    writer = ix.writer()
    
    # Check current Whoosh content
    existing_whoosh_ids = set()
    with ix.searcher() as searcher:
        for d in searcher.all_stored_fields():
            existing_whoosh_ids.add(d["id"])

    whoosh_added = 0
    for chunk in saved_chunks:
        cid_str = str(chunk["id"])
        if cid_str not in existing_whoosh_ids:
            writer.add_document(id=cid_str, text=chunk["text"])
            whoosh_added += 1

    writer.commit()
    print(f"✅ Whoosh updated: {whoosh_added} new chunks indexed.")

    # --- FINAL CLEANUP ---
    # Build helper maps
    meta_dict = {c["id"]: c for c in saved_chunks}
    with open(os.path.join(OUT_DIR, "chunks_dict.json"), "w", encoding="utf-8") as fh:
        json.dump(meta_dict, fh, ensure_ascii=False, indent=2)

    faiss_to_chunkid = {str(v): k for k, v in id_to_index.items()}
    with open(os.path.join(OUT_DIR, "faiss_to_chunkid.json"), "w", encoding="utf-8") as fh:
        json.dump(faiss_to_chunkid, fh, ensure_ascii=False, indent=2)

    # Clear retrieval pickle cache to force a fresh reload in hybrid_retrieval.py
    if os.path.exists(PKL_CACHE):
        os.remove(PKL_CACHE)
        print("🗑️ Stale metadata cache cleared.")

    print(f"✅ Everything is up to date.")


if __name__ == "__main__":
    main()