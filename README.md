# 🧪 Chemical Engineering Opportunity Finder & AI Application Assistant

An AI-powered Streamlit app that:

- Searches the **live web** for chemical engineering internships, fellowships,
  PhD/research positions, and lab/company contacts.
- Includes **site-restricted searches** on LinkedIn, X (Twitter), Instagram and
  Facebook to surface publicly posted opportunities on those platforms.
- Lets you **filter** by field, place, period, duration, funding type
  (Fully Funded / Partially Funded / Stipend / Unfunded), and degree level
  (Undergraduate / Master / PhD / Postdoc).
- Refreshes with a **new set of results every time you press "Search"**.
- Lets you build a **personal profile**: upload your CV, reference letters,
  certifications, transcripts, etc.
- Generates, per opportunity:
  - A personalized **motivation letter**
  - A personalized **outreach email**
  - **Tailored CV sections** (summary + reordered skills/experience)
  - All downloadable as `.docx`

---

## ⚠️ Important honesty note about social media

LinkedIn, X, Instagram and Facebook **block automated scraping** for
logged-out / unauthorized clients, and scraping them violates their Terms of
Service. This app does **not** log into those platforms or scrape them
directly. Instead, it performs public web searches restricted to those
domains (`site:linkedin.com`, `site:x.com`, etc.), which is the same
mechanism search engines themselves use, and is legal and durable. Results
from those platforms are clearly labeled by source.

For the best LinkedIn results, it's also worth manually checking
LinkedIn's own "Jobs" search with filters set to "Internship" — the app
will point you toward relevant public posts, but LinkedIn's internal search
(while logged in) will always be more complete for that platform specifically.

---

## 🚀 1. Run it locally (Windows / Mac / Linux)

1. Install Python 3.10+ if you don't have it.
2. Open a terminal in this folder and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Get a FREE Google Gemini API key (no credit card needed) at
   https://aistudio.google.com — sign in with your Google account, click
   "Get API Key" / "Create API Key", and copy it.
   (used to structure search results and write your letters/emails/CVs).

4. Run the app:

   ```bash
   streamlit run app.py
   ```

5. Your browser opens automatically at `http://localhost:8501`. Paste your
   API key into the sidebar, fill in your profile, upload your CV, set your
   filters, and click **Search for Opportunities**.

---

## 📱 2. Permanent solution you can use from your phone, anytime

The easiest free way to get a permanent URL you can open from any phone
browser (no app install needed) is **Streamlit Community Cloud**:

1. Create a free GitHub account (https://github.com) if you don't have one.
2. Create a new **public** GitHub repository (e.g. `cheme-opportunity-finder`)
   and upload all the files from this folder to it
   (`app.py`, `requirements.txt`, the `modules/` folder, etc.).
   - **Do NOT upload your real CV/profile_data folder** if the repo is public —
     keep that empty (the `.gitkeep` placeholder is fine). You'll upload your
     CV directly inside the running app instead.
3. Go to https://share.streamlit.io, sign in with GitHub, click
   **"New app"**, and select your repository + `app.py` as the entry point.
4. In the app's **Settings → Secrets**, add:

   ```
   GOOGLE_API_KEY = "your_key_here"
   ```

   (Optional — you can also just paste your key into the sidebar each time.)

5. Click **Deploy**. You'll get a permanent URL like:

   `https://your-app-name.streamlit.app`

6. Open that link on your phone, **add it to your home screen**
   (Share → "Add to Home Screen" on iOS, or the browser menu → "Add to Home
   Screen" / "Install App" on Android) — it will behave like a native app icon.

This URL works from any device, any time, with no installation, and is free
on Streamlit Community Cloud for personal projects.

### Notes on persistence in the cloud
Streamlit Cloud's filesystem can reset on redeploys, so uploaded CV/documents
may need to be re-uploaded occasionally. For a truly permanent personal
archive, you can:
- Re-upload your CV at the start of each session (quick — it's saved for the
  session), or
- Connect a small cloud storage (e.g. a private GitHub repo, Google Drive, or
  a service like Supabase) — this would be a future enhancement to
  `modules/profile_manager.py`.

---

## 🛠️ 3. How it works (file overview)

```
chem_eng_agent/
├── app.py                  # Main Streamlit app (UI, filters, results, downloads)
├── requirements.txt        # Python dependencies
├── .env.example             # Template for your API key
├── modules/
│   ├── search_engine.py    # Builds & runs live web searches (DuckDuckGo + site: filters)
│   ├── ai_engine.py         # Claude API calls: structuring results, letters, emails, CVs
│   └── profile_manager.py   # Saves/loads your CV & documents, extracts text
└── profile_data/            # Where your uploaded CV/docs are stored locally
```

---

## 🔧 4. Customizing

- **Add more job boards**: edit `GENERAL_SOURCES` in `modules/search_engine.py`
  (e.g. add `site:euraxess.ec.europa.eu`, specific university career pages,
  national funding agencies, etc.)
- **Change the AI model**: edit `MODEL` in `modules/ai_engine.py`.
- **Tweak letter/email/CV tone or length**: edit the prompts in
  `modules/ai_engine.py`.
- **Add more filters**: extend the filter UI in `app.py` and the
  `_build_queries()` / `matches_filters()` functions.

---

## 💡 Tips for best results

- Be specific in the "Field / specialization" box — e.g.
  "polymer chemistry", "process safety engineering", "battery materials" —
  rather than just "chemical engineering", to get more targeted results.
- Press **Search** a few times — each click rotates through a different
  random slice of search queries, so you'll surface new listings over time.
- Always double-check deadlines and application instructions on the
  original listing page before applying — AI summaries can occasionally
  be imprecise about dates.
- Review and personalize AI-generated letters/emails before sending —
  treat them as strong first drafts, not final copies.
