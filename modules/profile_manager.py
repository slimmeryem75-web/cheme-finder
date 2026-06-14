"""
profile_manager.py
Handles storing the user's profile (CV, reference letters, certificates)
and extracting plain text from uploaded PDFs / Word documents so it can be
fed into the AI prompts later.
"""

import os
import json
from pypdf import PdfReader
from docx import Document

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "..", "profile_data")
PROFILE_JSON = os.path.join(PROFILE_DIR, "profile.json")
OPPORTUNITIES_JSON = os.path.join(PROFILE_DIR, "opportunities.json")

os.makedirs(PROFILE_DIR, exist_ok=True)


def _extract_text_from_pdf(filepath: str) -> str:
    text = []
    reader = PdfReader(filepath)
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)


def _extract_text_from_docx(filepath: str) -> str:
    doc = Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(filepath: str) -> str:
    """Extract raw text from a pdf/docx/txt file."""
    ext = filepath.lower().split(".")[-1]
    try:
        if ext == "pdf":
            return _extract_text_from_pdf(filepath)
        elif ext in ("docx", "doc"):
            return _extract_text_from_docx(filepath)
        elif ext == "txt":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        else:
            return ""
    except Exception as e:
        return f"[Could not read {os.path.basename(filepath)}: {e}]"


def save_uploaded_file(uploaded_file, subfolder: str = "documents") -> str:
    """Save a Streamlit UploadedFile object to disk and return its path."""
    folder = os.path.join(PROFILE_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, uploaded_file.name)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filepath


def load_profile() -> dict:
    if os.path.exists(PROFILE_JSON):
        with open(PROFILE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "name": "",
        "summary": "",
        "documents": [],   # list of {filename, filepath, type, text}
        "cv_text": "",
    }


def save_profile(profile: dict):
    with open(PROFILE_JSON, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def add_document(uploaded_file, doc_type: str, profile: dict) -> dict:
    """Save file, extract its text, and register it in the profile dict."""
    filepath = save_uploaded_file(uploaded_file)
    text = extract_text(filepath)
    profile["documents"].append({
        "filename": uploaded_file.name,
        "filepath": filepath,
        "type": doc_type,
        "text": text,
    })
    if doc_type == "CV":
        profile["cv_text"] = text
    save_profile(profile)
    return profile


def get_combined_profile_text(profile: dict) -> str:
    """Return a single text blob combining CV + all supporting documents,
    used as context for the AI when writing letters/CVs."""
    parts = []
    if profile.get("summary"):
        parts.append("PERSONAL SUMMARY:\n" + profile["summary"])
    if profile.get("cv_text"):
        parts.append("CV CONTENT:\n" + profile["cv_text"])
    for doc in profile.get("documents", []):
        if doc["type"] != "CV":
            parts.append(f"{doc['type'].upper()} ({doc['filename']}):\n{doc['text'][:3000]}")
    return "\n\n---\n\n".join(parts)


# ----------------------------------------------------------------------
# Opportunities persistence
# ----------------------------------------------------------------------
def load_opportunities() -> list:
    """Load previously found opportunities from disk so they survive
    page refreshes / new sessions (as long as the app server itself
    hasn't been restarted/redeployed)."""
    if os.path.exists(OPPORTUNITIES_JSON):
        try:
            with open(OPPORTUNITIES_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_opportunities(opportunities: list):
    with open(OPPORTUNITIES_JSON, "w", encoding="utf-8") as f:
        json.dump(opportunities, f, ensure_ascii=False, indent=2)


def merge_opportunities(existing: list, new_items: list) -> list:
    """Merge newly found opportunities into the existing list,
    de-duplicating by link so nothing is lost between searches."""
    seen_links = {o.get("link") for o in existing if o.get("link")}
    merged = list(existing)
    added = 0
    for item in new_items:
        link = item.get("link")
        if link and link in seen_links:
            continue
        if link:
            seen_links.add(link)
        merged.append(item)
        added += 1
    return merged, added


def clear_opportunities():
    if os.path.exists(OPPORTUNITIES_JSON):
        os.remove(OPPORTUNITIES_JSON)
