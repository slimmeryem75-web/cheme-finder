"""
app.py
Chemical Engineering Opportunity Finder & AI Application Assistant
--------------------------------------------------------------------
A Streamlit app that:
  - Lets you build a personal profile (CV + supporting documents)
  - Searches the live web (incl. site-restricted searches on LinkedIn,
    X, Instagram, Facebook, and major job/fellowship boards) for
    internships, fellowships and research positions
  - Lets you filter by field, location, period, duration, funding type
    and degree level
  - Uses Claude to structure results into clean opportunity cards
  - Generates a personalized motivation letter, outreach email, and
    tailored CV section for any opportunity, downloadable as .docx

Run locally:
    pip install -r requirements.txt
    streamlit run app.py

Deploy for free, permanent, mobile-friendly access:
    See README.md for Streamlit Community Cloud deployment instructions.
"""

import os
import io
import random
import streamlit as st
from docx import Document

from modules import profile_manager as pm
from modules import search_engine as se
from modules import ai_engine as ai

# ----------------------------------------------------------------------
# Page setup & styling
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="ChemE Opportunity Finder",
    page_icon="🧪",
    layout="wide",
)

st.markdown("""
<style>
.opportunity-card {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 16px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
}
.opportunity-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1a3c40;
}
.opportunity-org {
    font-size: 0.95rem;
    color: #555;
    margin-bottom: 6px;
}
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 4px;
}
.badge-funding { background-color: #e6f4ea; color: #1e7e34; }
.badge-degree  { background-color: #e8f0fe; color: #1a73e8; }
.badge-field   { background-color: #fff4e5; color: #b35900; }
.badge-source  { background-color: #f3e8fd; color: #6a1b9a; }
.badge-deadline{ background-color: #fdeaea; color: #c62828; }
</style>
""", unsafe_allow_html=True)

st.title("🧪 Chemical Engineering Opportunity Finder")
st.caption(
    "Live search across the web (incl. LinkedIn / X / Instagram / Facebook public posts) "
    "for internships, fellowships, PhD positions, and lab/company contacts — "
    "plus AI-generated motivation letters, emails, and tailored CVs."
)

# ----------------------------------------------------------------------
# Session state init
# ----------------------------------------------------------------------
if "profile" not in st.session_state:
    st.session_state.profile = pm.load_profile()

if "opportunities" not in st.session_state:
    st.session_state.opportunities = []

if "search_seed" not in st.session_state:
    st.session_state.search_seed = random.randint(0, 1_000_000)


# ----------------------------------------------------------------------
# Helper: text -> docx bytes
# ----------------------------------------------------------------------
def text_to_docx_bytes(text: str, title: str = "") -> bytes:
    doc = Document()
    if title:
        doc.add_heading(title, level=1)
    for line in text.split("\n"):
        if line.strip().startswith("Subject:"):
            p = doc.add_paragraph()
            run = p.add_run(line)
            run.bold = True
        elif line.strip().upper() == line.strip() and len(line.strip()) > 3 and line.strip().isalpha() is False and line.strip() != "":
            # heuristics for ALL-CAPS section headers like "KEY SKILLS"
            doc.add_heading(line.strip(), level=2)
        else:
            doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ----------------------------------------------------------------------
# Sidebar: API key + Profile
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("🔑 AI API Key (Free)")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        type="password",
        value=os.environ.get("GOOGLE_API_KEY", ""),
        help="Required for structuring results and generating letters/CVs. "
             "Get a FREE key (no credit card) at aistudio.google.com. "
             "Stored only for this session."
    )
    if api_key_input:
        st.session_state["api_key"] = api_key_input

    st.divider()
    st.header("👤 Your Profile")

    profile = st.session_state.profile

    profile["name"] = st.text_input("Full name", value=profile.get("name", ""))
    profile["summary"] = st.text_area(
        "Short personal description / career goals",
        value=profile.get("summary", ""),
        height=120,
        placeholder="e.g. 3rd-year Chemical Engineering student interested in "
                    "sustainable polymers and process optimization, seeking "
                    "summer research internships in Europe..."
    )

    st.markdown("**Upload your documents**")
    doc_type = st.selectbox(
        "Document type",
        ["CV", "Reference Letter", "Certification", "Transcript", "Other"]
    )
    uploaded = st.file_uploader(
        "Drop a file (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=False,
        key="doc_uploader"
    )
    if uploaded is not None:
        if st.button("Save document", use_container_width=True):
            st.session_state.profile = pm.add_document(uploaded, doc_type, profile)
            st.success(f"Saved {uploaded.name} as {doc_type}")
            st.rerun()

    if profile.get("documents"):
        st.markdown("**Saved documents:**")
        for d in profile["documents"]:
            st.write(f"- {d['filename']}  _({d['type']})_")

    if st.button("💾 Save profile info", use_container_width=True):
        pm.save_profile(profile)
        st.success("Profile saved.")

# ----------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------
st.subheader("🔍 Search Filters")

col1, col2, col3 = st.columns(3)
with col1:
    field = st.text_input(
        "Field / specialization",
        value="chemical engineering",
        help="e.g. chemical engineering, catalysis, polymer science, process engineering, biotech"
    )
    place = st.text_input("Place (country/city, or 'Anywhere')", value="Anywhere")

with col2:
    degree = st.selectbox("Degree level", ["Any", "Undergraduate", "Master", "PhD", "Postdoc"])
    duration = st.selectbox("Duration", ["Any", "1-2 months", "3 months", "6 months", "1 year", "2+ years"])

with col3:
    funding = st.selectbox("Financement", ["Any", "Fully Funded", "Partially Funded", "Stipend", "Unfunded"])
    period = st.selectbox("Period", ["Any", "Summer 2026", "Fall 2026", "Spring 2027", "Rolling / Year-round"])

include_social = st.checkbox(
    "Include LinkedIn / X / Instagram / Facebook public posts in search",
    value=True
)

search_clicked = st.button("🔄  Search for Opportunities", type="primary", use_container_width=True)

# ----------------------------------------------------------------------
# Run search
# ----------------------------------------------------------------------
if search_clicked:
    if "api_key" not in st.session_state or not st.session_state["api_key"]:
        st.error("Please enter your Google Gemini API key in the sidebar first.")
    else:
        # New random seed each click -> different query slice -> fresh results
        st.session_state.search_seed = random.randint(0, 1_000_000)

        with st.spinner("Searching the web for opportunities..."):
            raw = se.search_opportunities(
                field=field,
                place=place,
                degree=degree,
                funding=funding,
                duration=duration,
                period=period,
                include_social=include_social,
                seed=st.session_state.search_seed,
            )

        with st.spinner("Organizing results with AI..."):
            structured = ai.structure_opportunities(raw, field, api_key=st.session_state["api_key"])

        st.session_state.opportunities = structured
        if not structured:
            st.warning("No structured opportunities found this time — try clicking Search again "
                       "(results rotate each time) or loosen your filters.")

# ----------------------------------------------------------------------
# Apply filters to existing results (client-side refine, no new search)
# ----------------------------------------------------------------------
def matches_filters(opp):
    if degree != "Any" and opp.get("degree_level") not in (degree, "Any", "Not specified"):
        return False
    if funding != "Any" and opp.get("funding") not in (funding, "Not specified"):
        return False
    return True

display_list = [o for o in st.session_state.opportunities if matches_filters(o)]

# ----------------------------------------------------------------------
# Display results
# ----------------------------------------------------------------------
st.subheader(f"📋 Opportunities ({len(display_list)})")

if not display_list:
    st.info("No opportunities loaded yet. Set your filters above and click **Search for Opportunities**.")
else:
    for idx, opp in enumerate(display_list):
        with st.container():
            st.markdown(f"""
<div class="opportunity-card">
  <div class="opportunity-title">{opp.get('title','Untitled')}</div>
  <div class="opportunity-org">{opp.get('organization','Unknown organization')} — {opp.get('location','Not specified')}</div>
  <span class="badge badge-deadline">⏰ Deadline: {opp.get('deadline','Not specified')}</span>
  <span class="badge badge-funding">💰 {opp.get('funding','Not specified')}</span>
  <span class="badge badge-degree">🎓 {opp.get('degree_level','Not specified')}</span>
  <span class="badge badge-field">🧪 {opp.get('field','Not specified')}</span>
  <span class="badge badge-source">🌐 {opp.get('source','Web')}</span>
  <p style="margin-top:8px;">{opp.get('summary','')}</p>
  <p style="font-size:0.85rem; color:#777;">
    📅 Period: {opp.get('period','Not specified')} &nbsp;|&nbsp;
    ⌛ Duration: {opp.get('duration','Not specified')} &nbsp;|&nbsp;
    📧 Contact: {opp.get('contact','Not specified')}
  </p>
  <a href="{opp.get('link','#')}" target="_blank">🔗 Open original listing</a>
</div>
""", unsafe_allow_html=True)

            with st.expander("✨ Generate personalized application materials"):
                profile_text = pm.get_combined_profile_text(st.session_state.profile)
                if not profile_text.strip():
                    st.warning("Upload your CV in the sidebar first so materials can be personalized.")
                else:
                    bcol1, bcol2, bcol3 = st.columns(3)

                    with bcol1:
                        if st.button("📝 Motivation Letter", key=f"letter_{idx}"):
                            with st.spinner("Writing motivation letter..."):
                                letter = ai.generate_motivation_letter(
                                    profile_text, opp, api_key=st.session_state["api_key"]
                                )
                            st.session_state[f"letter_text_{idx}"] = letter

                    with bcol2:
                        if st.button("📧 Outreach Email", key=f"email_{idx}"):
                            with st.spinner("Writing email..."):
                                email = ai.generate_email(
                                    profile_text, opp, api_key=st.session_state["api_key"]
                                )
                            st.session_state[f"email_text_{idx}"] = email

                    with bcol3:
                        if st.button("📄 Tailored CV Sections", key=f"cv_{idx}"):
                            with st.spinner("Tailoring CV..."):
                                cv_text = ai.generate_tailored_cv_sections(
                                    profile_text, opp, api_key=st.session_state["api_key"]
                                )
                            st.session_state[f"cv_text_{idx}"] = cv_text

                    if f"letter_text_{idx}" in st.session_state:
                        st.text_area("Motivation Letter", st.session_state[f"letter_text_{idx}"], height=300, key=f"letter_area_{idx}")
                        st.download_button(
                            "⬇️ Download Letter (.docx)",
                            data=text_to_docx_bytes(st.session_state[f"letter_text_{idx}"], "Motivation Letter"),
                            file_name=f"motivation_letter_{idx+1}.docx",
                            key=f"dl_letter_{idx}"
                        )

                    if f"email_text_{idx}" in st.session_state:
                        st.text_area("Outreach Email", st.session_state[f"email_text_{idx}"], height=200, key=f"email_area_{idx}")
                        st.download_button(
                            "⬇️ Download Email (.docx)",
                            data=text_to_docx_bytes(st.session_state[f"email_text_{idx}"], "Outreach Email"),
                            file_name=f"email_{idx+1}.docx",
                            key=f"dl_email_{idx}"
                        )

                    if f"cv_text_{idx}" in st.session_state:
                        st.text_area("Tailored CV Sections", st.session_state[f"cv_text_{idx}"], height=300, key=f"cv_area_{idx}")
                        st.download_button(
                            "⬇️ Download CV Sections (.docx)",
                            data=text_to_docx_bytes(st.session_state[f"cv_text_{idx}"], "Tailored CV Sections"),
                            file_name=f"tailored_cv_{idx+1}.docx",
                            key=f"dl_cv_{idx}"
                        )

st.divider()
st.caption(
    "⚠️ Always verify deadlines and details on the original listing before applying. "
    "AI-generated text should be reviewed and personalized further before sending."
)
