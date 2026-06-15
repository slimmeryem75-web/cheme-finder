"""
app.py – ChemE Opportunity Finder (Upgraded UI)
Multi-page Streamlit app with category home screen, list view, and detail view.
"""

import os
import io
import random
import streamlit as st
from docx import Document

from modules import profile_manager as pm
from modules import search_engine as se
from modules import ai_engine as ai

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ChemE Opportunity Finder",
    page_icon="🧪",
    layout="wide",
)

# ─────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Category cards ── */
.cat-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-top: 12px;
}
.cat-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 32px 24px 28px;
    text-align: center;
    cursor: pointer;
    border: 2px solid transparent;
    box-shadow: 0 4px 18px rgba(0,0,0,0.07);
    transition: all .18s ease;
}
.cat-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(0,0,0,0.12);
}
.cat-icon { font-size: 2.4rem; margin-bottom: 10px; }
.cat-title { font-size: 1.05rem; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; }
.cat-desc  { font-size: 0.82rem; color: #6b7280; }

/* ── Opportunity list cards ── */
.opp-card {
    background: #ffffff;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
    border: 1.5px solid #f0f0f5;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: box-shadow .15s;
}
.opp-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.10); }
.opp-title { font-size: 1rem; font-weight: 700; color: #111827; }
.opp-org   { font-size: 0.88rem; color: #6b7280; margin-top: 2px; }
.opp-meta  { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }

/* ── Badges ── */
.badge {
    display: inline-flex; align-items: center;
    padding: 3px 11px; border-radius: 999px;
    font-size: 0.73rem; font-weight: 600;
}
.b-country  { background: #eff6ff; color: #1d4ed8; }
.b-field    { background: #fff7ed; color: #c2410c; }
.b-fund     { background: #f0fdf4; color: #166534; }
.b-degree   { background: #faf5ff; color: #7e22ce; }
.b-deadline { background: #fef2f2; color: #b91c1c; }
.b-type     { background: #ecfeff; color: #0e7490; }

/* ── Detail page ── */
.detail-header {
    background: linear-gradient(135deg, #1a3c5e 0%, #0d6eaa 100%);
    border-radius: 18px;
    padding: 32px 36px;
    color: white;
    margin-bottom: 24px;
}
.detail-title { font-size: 1.5rem; font-weight: 700; line-height: 1.3; }
.detail-org   { font-size: 1rem; opacity: .85; margin-top: 6px; }

/* ── Back / Home nav ── */
.top-nav {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px;
}

/* ── Section headings ── */
.section-label {
    font-size: 0.75rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #9ca3af; margin-bottom: 6px;
}

/* ── Hero tagline ── */
.hero-sub {
    font-size: 1rem; color: #6b7280; max-width: 520px; margin: 0 auto 32px;
    line-height: 1.6; text-align: center;
}
.hero-title {
    font-size: 2rem; font-weight: 800; color: #111827;
    text-align: center; margin-bottom: 8px;
}

/* hide streamlit chrome */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "profile" not in st.session_state:
    st.session_state.profile = pm.load_profile()
if "opportunities" not in st.session_state:
    st.session_state.opportunities = pm.load_opportunities()
if "search_seed" not in st.session_state:
    st.session_state.search_seed = random.randint(0, 1_000_000)
if "api_key" not in st.session_state:
    st.session_state["api_key"] = os.environ.get("GROQ_API_KEY", "")

# Navigation state: "home" | "list" | "detail"
if "page" not in st.session_state:
    st.session_state.page = "home"
if "category" not in st.session_state:
    st.session_state.category = None
if "selected_opp" not in st.session_state:
    st.session_state.selected_opp = None


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
CATEGORIES = [
    {
        "key": "phd",
        "icon": "🎓",
        "title": "PhD Positions",
        "desc": "Doctoral programmes & funded research posts",
        "color": "#4f46e5",
        "opp_type": "PhD Position",
        "field_hint": "chemical engineering PhD",
    },
    {
        "key": "industrial",
        "icon": "🏭",
        "title": "Industrial Internships",
        "desc": "Hands-on placements in industry & companies",
        "color": "#0891b2",
        "opp_type": "Internship",
        "field_hint": "chemical engineering industrial internship",
    },
    {
        "key": "research",
        "icon": "🔬",
        "title": "Research Internships",
        "desc": "Lab & university research programmes",
        "color": "#059669",
        "opp_type": "Research Position",
        "field_hint": "chemical engineering research internship",
    },
    {
        "key": "other",
        "icon": "🌟",
        "title": "Other Opportunities",
        "desc": "Fellowships, scholarships, summer programmes",
        "color": "#d97706",
        "opp_type": "Fellowship",
        "field_hint": "chemical engineering fellowship scholarship",
    },
]

CAT_MAP = {c["key"]: c for c in CATEGORIES}


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


def get_category_opps(cat_key):
    cat = CAT_MAP[cat_key]
    keyword = cat["opp_type"].lower()
    result = []
    for o in reversed(st.session_state.opportunities):
        title_l = o.get("title", "").lower()
        summary_l = o.get("summary", "").lower()
        if keyword in title_l or keyword in summary_l:
            result.append(o)
    return result


def nav_home():
    st.session_state.page = "home"
    st.session_state.category = None
    st.session_state.selected_opp = None


def nav_list(cat_key):
    st.session_state.page = "list"
    st.session_state.category = cat_key


def nav_detail(opp):
    st.session_state.selected_opp = opp
    st.session_state.page = "detail"


# ─────────────────────────────────────────────
# Sidebar (always visible)
# ─────────────────────────────────────────────
with st.sidebar:
    # Home button
    if st.button("🏠  Home", use_container_width=True):
        nav_home()
        st.rerun()

    st.divider()
    st.header("🔑 Groq API Key")
    st.text_input(
        "Groq API Key",
        type="password",
        help="Free key at https://console.groq.com",
        key="api_key",
    )

    st.divider()
    st.header("👤 Your Profile")
    profile = st.session_state.profile
    profile["name"] = st.text_input("Full name", value=profile.get("name", ""))
    profile["summary"] = st.text_area(
        "Personal description / goals",
        value=profile.get("summary", ""),
        height=160,
        placeholder="e.g. 3rd-year Chemical Engineering student interested in sustainable polymers…",
    )
    if st.button("💾 Save profile", use_container_width=True):
        pm.save_profile(profile)
        st.success("Profile saved.")

    st.divider()

    # ── Filters (sidebar, shown on list page) ──
    if st.session_state.page in ("list", "detail"):
        st.header("🔍 Filters")

        cat = CAT_MAP.get(st.session_state.category, CATEGORIES[0])

        field = st.text_input(
            "Field / specialization",
            value=cat["field_hint"],
            key="sb_field",
        )
        place = st.text_input("Country / city", value="Anywhere", key="sb_place")
        degree = st.selectbox(
            "Degree level",
            ["Any", "Undergraduate", "Master", "PhD", "Postdoc"],
            key="sb_degree",
        )
        funding = st.selectbox(
            "Funding",
            ["Any", "Fully Funded", "Partially Funded", "Stipend", "Unfunded"],
            key="sb_funding",
        )
        duration = st.selectbox(
            "Duration",
            ["Any", "1-2 months", "3 months", "6 months", "1 year", "2+ years"],
            key="sb_duration",
        )
        period = st.selectbox(
            "Period",
            ["Any", "Summer 2026", "Fall 2026", "Spring 2027", "Rolling / Year-round"],
            key="sb_period",
        )
        include_social = st.checkbox("Include LinkedIn / social", value=True, key="sb_social")

        if st.button("🔄 Search Opportunities", type="primary", use_container_width=True):
            if not st.session_state.get("api_key"):
                st.error("Enter your Groq API key above first.")
            else:
                st.session_state.search_seed = random.randint(0, 1_000_000)
                with st.spinner("Searching the web…"):
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
                if not raw:
                    st.error("No results. DuckDuckGo may be rate-limiting — wait 30 s and retry.")
                else:
                    st.info(f"Found {len(raw)} raw results — organising with AI…")
                    with st.spinner("Organising results…"):
                        structured = ai.structure_opportunities(
                            raw, field, api_key=st.session_state["api_key"]
                        )
                    if not structured:
                        st.warning("AI could not extract opportunities. Check your key.")
                    else:
                        merged, added = pm.merge_opportunities(
                            st.session_state.opportunities, structured
                        )
                        st.session_state.opportunities = merged
                        pm.save_opportunities(merged)
                        st.success(f"✅ Added {added} new opportunit{'y' if added==1 else 'ies'}.")
                        st.rerun()


# ═══════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════
if st.session_state.page == "home":
    st.markdown('<div class="hero-title">🧪 ChemE Opportunity Finder</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-sub">Discover internships, PhD positions, research programmes, '
        'and fellowships — powered by live web search and AI assistance.</div>',
        unsafe_allow_html=True,
    )

    # Count per category
    total = len(st.session_state.opportunities)
    counts = {}
    for cat in CATEGORIES:
        counts[cat["key"]] = len(get_category_opps(cat["key"]))

    # Render category grid using columns (2×2)
    row1 = CATEGORIES[:2]
    row2 = CATEGORIES[2:]

    for row in (row1, row2):
        cols = st.columns(2, gap="medium")
        for col, cat in zip(cols, row):
            with col:
                n = counts[cat["key"]]
                label = f"{n} saved" if n else "No results yet"
                # Use a styled button with markdown above it
                st.markdown(
                    f"""
                    <div style="
                        background:#fff; border-radius:18px; padding:30px 20px 16px;
                        text-align:center; border:2px solid #f3f4f6;
                        box-shadow:0 4px 18px rgba(0,0,0,0.07); margin-bottom:4px;">
                      <div style="font-size:2.2rem">{cat['icon']}</div>
                      <div style="font-size:1.05rem;font-weight:700;color:#111827;margin:8px 0 4px">{cat['title']}</div>
                      <div style="font-size:0.82rem;color:#6b7280;margin-bottom:12px">{cat['desc']}</div>
                      <div style="font-size:0.78rem;font-weight:600;color:{cat['color']}">{label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"Explore {cat['title']}", key=f"cat_{cat['key']}", use_container_width=True):
                    nav_list(cat["key"])
                    st.rerun()

    st.divider()
    st.caption(
        f"📊 {total} opportunities saved in total · "
        "Use the **Filters** panel (appears after selecting a category) to search for more."
    )


# ═══════════════════════════════════════════════════════════
# PAGE: LIST
# ═══════════════════════════════════════════════════════════
elif st.session_state.page == "list":
    cat = CAT_MAP[st.session_state.category]

    # Breadcrumb
    st.markdown(
        f"<div style='color:#6b7280;font-size:0.85rem;margin-bottom:6px'>"
        f"🏠 Home &rsaquo; {cat['icon']} {cat['title']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"## {cat['icon']} {cat['title']}")

    # Search bar at top
    search_q = st.text_input("", placeholder="🔍  Search within results…", label_visibility="collapsed")

    opps = get_category_opps(cat["key"])

    # Apply local search filter
    if search_q:
        q_lower = search_q.lower()
        opps = [
            o for o in opps
            if q_lower in o.get("title", "").lower()
            or q_lower in o.get("organization", "").lower()
            or q_lower in o.get("field", "").lower()
            or q_lower in o.get("location", "").lower()
        ]

    if not opps:
        st.info(
            f"No {cat['title'].lower()} saved yet. "
            "Use the **Filters** panel on the left to search for opportunities."
        )
    else:
        st.markdown(f"<div style='color:#6b7280;font-size:0.85rem;margin-bottom:12px'>{len(opps)} opportunities</div>", unsafe_allow_html=True)
        for idx, opp in enumerate(opps):
            title = opp.get("title", "Untitled")
            org   = opp.get("organization", "Unknown")
            loc   = opp.get("location", "Not specified")
            field_val = opp.get("field", "Not specified")
            funding_val = opp.get("funding", "")
            deadline_val = opp.get("deadline", "")
            degree_val = opp.get("degree_level", "")

            badges = ""
            if loc and loc != "Not specified":
                badges += f'<span class="badge b-country">📍 {loc}</span>'
            if field_val and field_val != "Not specified":
                badges += f'<span class="badge b-field">🔬 {field_val}</span>'
            if funding_val and funding_val != "Not specified":
                badges += f'<span class="badge b-fund">💰 {funding_val}</span>'
            if degree_val and degree_val not in ("Not specified", "Any"):
                badges += f'<span class="badge b-degree">🎓 {degree_val}</span>'
            if deadline_val and deadline_val != "Not specified":
                badges += f'<span class="badge b-deadline">⏰ {deadline_val}</span>'

            st.markdown(
                f"""
                <div class="opp-card">
                  <div class="opp-title">{title}</div>
                  <div class="opp-org">{org}</div>
                  <div class="opp-meta">{badges}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("View details →", key=f"detail_{idx}", use_container_width=False):
                nav_detail(opp)
                st.rerun()
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# PAGE: DETAIL
# ═══════════════════════════════════════════════════════════
elif st.session_state.page == "detail":
    opp = st.session_state.selected_opp
    cat = CAT_MAP.get(st.session_state.category, CATEGORIES[0])

    # Breadcrumb nav
    col_back, col_home, _ = st.columns([1.2, 1, 6])
    with col_back:
        if st.button("← Back"):
            st.session_state.page = "list"
            st.rerun()
    with col_home:
        if st.button("🏠 Home"):
            nav_home()
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Header banner
    title = opp.get("title", "Untitled")
    org   = opp.get("organization", "")
    st.markdown(
        f"""
        <div class="detail-header">
          <div class="detail-title">{title}</div>
          <div class="detail-org">{cat['icon']} {org}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Key details grid
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="section-label">Location</div>', unsafe_allow_html=True)
        st.markdown(f"📍 {opp.get('location','Not specified')}")
        st.markdown('<div class="section-label" style="margin-top:16px">Field</div>', unsafe_allow_html=True)
        st.markdown(f"🔬 {opp.get('field','Not specified')}")
    with c2:
        st.markdown('<div class="section-label">Funding</div>', unsafe_allow_html=True)
        st.markdown(f"💰 {opp.get('funding','Not specified')}")
        st.markdown('<div class="section-label" style="margin-top:16px">Degree Level</div>', unsafe_allow_html=True)
        st.markdown(f"🎓 {opp.get('degree_level','Not specified')}")
    with c3:
        st.markdown('<div class="section-label">Deadline</div>', unsafe_allow_html=True)
        st.markdown(f"⏰ {opp.get('deadline','Not specified')}")
        st.markdown('<div class="section-label" style="margin-top:16px">Duration</div>', unsafe_allow_html=True)
        st.markdown(f"⌛ {opp.get('duration','Not specified')}")

    st.divider()

    # Full description
    st.subheader("📋 About this Opportunity")
    summary = opp.get("summary", "No description available.")
    st.markdown(summary)

    extra_fields = {
        "Period": opp.get("period"),
        "Contact": opp.get("contact"),
        "Source": opp.get("source"),
    }
    for label, val in extra_fields.items():
        if val and val not in ("Not specified", None, ""):
            st.markdown(f"**{label}:** {val}")

    link = opp.get("link", "")
    if link and link != "#":
        st.link_button("🔗 Open original listing", link)

    st.divider()

    # Motivation letter
    st.subheader("✨ Generate Motivation Letter")
    profile = st.session_state.profile
    has_profile = bool(profile.get("name") or profile.get("summary"))

    if not has_profile:
        st.warning("Fill in your name and personal description in the sidebar so the AI can personalise your letter.")
    else:
        if st.button("📝 Generate Motivation Letter", type="primary"):
            if not st.session_state.get("api_key"):
                st.error("❌ Enter your Groq API key in the sidebar first.")
            else:
                profile_text = pm.get_profile_text(profile)
                with st.spinner("Writing your letter…"):
                    try:
                        letter = ai.generate_motivation_letter(
                            profile_text, opp, api_key=st.session_state["api_key"]
                        )
                        st.session_state["detail_letter"] = letter
                    except RuntimeError as e:
                        st.error(f"❌ {e}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {e}")

        if "detail_letter" in st.session_state:
            st.text_area("Motivation Letter", st.session_state["detail_letter"], height=400)
            st.download_button(
                "⬇️ Download as .docx",
                data=text_to_docx_bytes(st.session_state["detail_letter"], "Motivation Letter"),
                file_name="motivation_letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    st.divider()
    st.caption("⚠️ Always verify deadlines on the original listing. Review and personalise AI-generated text before sending.")
