"""
app.py
Chemical Engineering Opportunity Finder & AI Application Assistant
Uses Groq (free, no credit card) for AI features.
Get your free Groq key at https://console.groq.com
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
.badge-funding  { background-color: #e6f4ea; color: #1e7e34; }
.badge-degree   { background-color: #e8f0fe; color: #1a73e8; }
.badge-field    { background-color: #fff4e5; color: #b35900; }
.badge-source   { background-color: #f3e8fd; color: #6a1b9a; }
.badge-deadline { background-color: #fdeaea; color: #c62828; }
.badge-type     { background-color: #e0f7fa; color: #00695c; }
</style>
""", unsafe_allow_html=True)

st.title("🧪 Chemical Engineering Opportunity Finder")
st.caption(
    "Live search across the web for internships, fellowships, scholarships, "
    "summer programs, and PhD positions — plus AI-generated motivation letters."
)

# ----------------------------------------------------------------------
# Session state init
# ----------------------------------------------------------------------
if "profile" not in st.session_state:
    st.session_state.profile = pm.load_profile()

if "opportunities" not in st.session_state:
    st.session_state.opportunities = pm.load_opportunities()

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
        elif (
            line.strip().upper() == line.strip()
            and len(line.strip()) > 3
            and line.strip() != ""
        ):
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
    st.header("🔑 Groq API Key (Free)")
    api_key_input = st.text_input(
        "Groq API Key",
        type="password",
        value=os.environ.get("GROQ_API_KEY", ""),
        help=(
            "100% free, no credit card needed. "
            "Get your key at https://console.groq.com"
        ),
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
        height=180,
        placeholder=(
            "e.g. 3rd-year Chemical Engineering student interested in "
            "sustainable polymers and process optimization. "
            "Experience with Python, MATLAB, and lab work in catalysis. "
            "Looking for research internships in Europe or North America..."
        ),
    )

    if st.button("💾 Save profile", use_container_width=True):
        pm.save_profile(profile)
        st.success("Profile saved.")

# ----------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------
st.subheader("🔍 Search Filters")

col1, col2, col3, col4 = st.columns(4)
with col1:
    field = st.text_input(
        "Field / specialization",
        value="chemical engineering",
        placeholder="e.g. polymer chemistry, process safety...",
    )
    place = st.text_input("Place (country/city, or 'Anywhere')", value="Anywhere")

with col2:
    opp_type = st.selectbox(
        "Opportunity type",
        ["Any", "Internship", "Fellowship", "Scholarship", "Summer Program", "PhD Position", "Research Position"],
    )
    degree = st.selectbox(
        "Degree level", ["Any", "Undergraduate", "Master", "PhD", "Postdoc"]
    )

with col3:
    funding = st.selectbox(
        "Funding",
        ["Any", "Fully Funded", "Partially Funded", "Stipend", "Unfunded"],
    )
    duration = st.selectbox(
        "Duration",
        ["Any", "1-2 months", "3 months", "6 months", "1 year", "2+ years"],
    )

with col4:
    period = st.selectbox(
        "Period",
        ["Any", "Summer 2026", "Fall 2026", "Spring 2027", "Rolling / Year-round"],
    )
    include_social = st.checkbox(
        "Include LinkedIn / X / social media",
        value=True,
    )

search_clicked = st.button(
    "🔄  Search for Opportunities", type="primary", use_container_width=True
)

# ----------------------------------------------------------------------
# Test API key button
# ----------------------------------------------------------------------
if st.button("🧪 Test Groq API Key", use_container_width=True):
    if "api_key" not in st.session_state or not st.session_state["api_key"]:
        st.error("Enter your Groq API key in the sidebar first.")
    else:
        import requests as _req
        key = st.session_state["api_key"]
        try:
            r = _req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Say hello in one word."}],
                },
                timeout=15,
            )
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"]
                st.success(f"✅ Groq API works! Response: {reply.strip()}")
            else:
                err = r.json().get("error", {}).get("message", "unknown error")
                st.error(f"❌ HTTP {r.status_code} — {err}")
        except Exception as e:
            st.error(f"❌ Exception: {e}")

# ----------------------------------------------------------------------
# Run search
# ----------------------------------------------------------------------
if search_clicked:
    if "api_key" not in st.session_state or not st.session_state["api_key"]:
        st.error("Please enter your Groq API key in the sidebar first.")
    else:
        st.session_state.search_seed = random.randint(0, 1_000_000)

        search_field = field
        if opp_type != "Any":
            search_field = f"{field} {opp_type}"

        with st.spinner("Searching the web for opportunities..."):
            raw = se.search_opportunities(
                field=search_field,
                place=place,
                degree=degree,
                funding=funding,
                duration=duration,
                period=period,
                include_social=include_social,
                seed=st.session_state.search_seed,
            )

        if not raw:
            st.error(
                "⚠️ Web search returned 0 results. "
                "DuckDuckGo may be rate-limiting. Wait 30 seconds and try again."
            )
        else:
            st.info(f"🔎 Found {len(raw)} raw results — asking AI to structure them...")
            with st.spinner("Organizing results with AI..."):
                structured = ai.structure_opportunities(
                    raw, search_field, api_key=st.session_state["api_key"]
                )
            if not structured:
                st.warning(
                    "AI could not extract structured opportunities. "
                    "Check your Groq API key and try a more specific field."
                )
            else:
                merged, added = pm.merge_opportunities(
                    st.session_state.opportunities, structured
                )
                st.session_state.opportunities = merged
                pm.save_opportunities(merged)
                st.success(
                    f"✅ Added {added} new opportunit{'y' if added == 1 else 'ies'} "
                    f"(total saved so far: {len(merged)})."
                )

# ----------------------------------------------------------------------
# Client-side filter on existing results
# ----------------------------------------------------------------------
def matches_filters(opp):
    if degree != "Any" and opp.get("degree_level") not in (degree, "Any", "Not specified"):
        return False
    if funding != "Any" and opp.get("funding") not in (funding, "Not specified"):
        return False
    if opp_type != "Any":
        title_lower = opp.get("title", "").lower()
        summary_lower = opp.get("summary", "").lower()
        keyword = opp_type.lower()
        if keyword not in title_lower and keyword not in summary_lower:
            return False
    return True


display_list = [o for o in st.session_state.opportunities if matches_filters(o)]

# ----------------------------------------------------------------------
# Display results
# ----------------------------------------------------------------------
st.subheader(f"📋 Opportunities ({len(display_list)})")

if st.session_state.opportunities:
    if st.button("🗑️ Clear all saved opportunities"):
        st.session_state.opportunities = []
        pm.clear_opportunities()
        st.rerun()

if not display_list:
    st.info(
        "No opportunities loaded yet. Set your filters above and click **Search for Opportunities**."
    )
else:
    for idx, opp in enumerate(display_list):
        with st.container():
            st.markdown(
                f"""
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
""",
                unsafe_allow_html=True,
            )

            with st.expander("✨ Generate motivation letter"):
                profile = st.session_state.profile
                has_profile = bool(profile.get("name") or profile.get("summary"))

                if not has_profile:
                    st.warning(
                        "⚠️ Please fill in your name and personal description in the sidebar "
                        "so the AI can personalize your letter."
                    )
                else:
                    if st.button("📝 Generate Motivation Letter", key=f"letter_{idx}"):
                        profile_text = pm.get_profile_text(profile)
                        with st.spinner("Writing motivation letter..."):
                            letter = ai.generate_motivation_letter(
                                profile_text, opp, api_key=st.session_state["api_key"]
                            )
                        st.session_state[f"letter_text_{idx}"] = letter

                    if f"letter_text_{idx}" in st.session_state:
                        st.text_area(
                            "Motivation Letter",
                            st.session_state[f"letter_text_{idx}"],
                            height=350,
                            key=f"letter_area_{idx}",
                        )
                        st.download_button(
                            "⬇️ Download Letter (.docx)",
                            data=text_to_docx_bytes(
                                st.session_state[f"letter_text_{idx}"], "Motivation Letter"
                            ),
                            file_name=f"motivation_letter_{idx+1}.docx",
                            key=f"dl_letter_{idx}",
                        )

st.divider()
st.caption(
    "⚠️ Always verify deadlines and details on the original listing before applying. "
    "AI-generated text should be reviewed and personalized further before sending."
)
