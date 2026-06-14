"""
ai_engine.py
Wraps calls to Google's Gemini API (FREE tier, no credit card required) for:
 1. Turning raw search results into structured opportunity cards
    (title, organization, location, deadline, period, funding, field, contact)
 2. Generating a personalized motivation letter
 3. Generating a personalized outreach email
 4. Generating a tailored CV summary/bullet-points for a specific opportunity

Get a free API key at https://aistudio.google.com (no credit card needed).
Set it as the GOOGLE_API_KEY environment variable, or enter it in the app
sidebar.
"""

import json
import os
import google.generativeai as genai

MODEL = "gemini-2.5-flash"


def _model(api_key: str = None):
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("No Google Gemini API key provided.")
    genai.configure(api_key=key)
    return genai.GenerativeModel(MODEL)


def _generate(prompt: str, api_key: str = None, max_tokens: int = 1500) -> str:
    model = _model(api_key)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
        ),
    )
    return response.text


def structure_opportunities(raw_results: list, field: str, api_key: str = None) -> list:
    """
    Send a batch of raw search results to Gemini and ask it to extract
    structured opportunity info. Returns a list of dicts with keys:
    title, organization, location, deadline, period, duration, funding,
    degree_level, field, contact, link, summary
    """
    if not raw_results:
        return []

    structured = []
    chunk_size = 8
    for i in range(0, len(raw_results), chunk_size):
        chunk = raw_results[i:i + chunk_size]
        chunk = [r for r in chunk if r.get("source") != "Error" and r.get("link")]
        if not chunk:
            continue

        listing_text = ""
        for idx, r in enumerate(chunk):
            listing_text += (
                f"\n[{idx}]\nTitle: {r['title']}\nSource platform: {r['source']}\n"
                f"Link: {r['link']}\nSnippet: {r['snippet']}\n"
            )

        prompt = f"""You are helping a chemical engineering student/researcher find real
internships, fellowships, PhD positions, and lab/company contacts.

Below is a list of raw web search results. For EACH item, extract what you can
into a structured JSON object. If information is not present in the snippet,
make a reasonable best guess based on context, or use "Not specified".
Do NOT invent fake links or contacts - only use what's given.

Discard items that are clearly irrelevant (not about internships, fellowships,
PhD/research positions, or job opportunities for chemical engineers / related
fields like materials science, process engineering, energy, biotech, etc.)
by simply not including them in the output.

For each relevant item return an object with these fields:
- "title": short opportunity title
- "organization": company, university, or lab name
- "location": city/country or "Remote"/"Not specified"
- "deadline": application deadline if mentioned, else "Not specified"
- "period": e.g. "Summer 2026", "Fall 2026", or "Not specified"
- "duration": e.g. "3 months", "6 months", "1 year", or "Not specified"
- "funding": one of ["Fully Funded", "Partially Funded", "Stipend", "Unfunded", "Not specified"]
- "degree_level": one of ["Undergraduate", "Master", "PhD", "Postdoc", "Any", "Not specified"]
- "field": specific sub-field (e.g. "Process Engineering", "Materials Science", "Catalysis")
- "contact": email or contact person if mentioned, else "Not specified"
- "source": the source platform given
- "link": the link given
- "summary": 1-2 sentence plain-language summary of the opportunity

Search field of interest: {field}

Raw results:
{listing_text}

Return ONLY a valid JSON array of objects, nothing else. No markdown fences, no preamble."""

        try:
            text = _generate(prompt, api_key=api_key, max_tokens=2500).strip()
        except Exception:
            continue

        # strip accidental markdown fences
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            items = json.loads(text)
            structured.extend(items)
        except json.JSONDecodeError:
            continue

    return structured


def generate_motivation_letter(profile_text: str, opportunity: dict, api_key: str = None) -> str:
    prompt = f"""Write a personalized, professional motivation letter (cover letter) for the
following opportunity, written in first person as the applicant.

APPLICANT BACKGROUND (from their CV and documents):
{profile_text[:6000]}

OPPORTUNITY DETAILS:
Title: {opportunity.get('title')}
Organization: {opportunity.get('organization')}
Location: {opportunity.get('location')}
Field: {opportunity.get('field')}
Degree level: {opportunity.get('degree_level')}
Summary: {opportunity.get('summary')}

Instructions:
- 350-450 words
- Highlight relevant skills/experience from the applicant's background that match this specific opportunity
- Professional but warm tone
- Include a clear opening, body paragraphs connecting background to the role, and a closing
- Do not invent specific achievements that are not supported by the background text
- Output plain text only, ready to copy into a document"""

    return _generate(prompt, api_key=api_key, max_tokens=1200)


def generate_email(profile_text: str, opportunity: dict, api_key: str = None) -> str:
    prompt = f"""Write a short, polite, personalized outreach email (with subject line) to inquire
about or apply for the following opportunity. If a contact person/email is
given, address it to them; otherwise use a generic professional greeting.

APPLICANT BACKGROUND:
{profile_text[:4000]}

OPPORTUNITY DETAILS:
Title: {opportunity.get('title')}
Organization: {opportunity.get('organization')}
Contact: {opportunity.get('contact')}
Field: {opportunity.get('field')}
Summary: {opportunity.get('summary')}

Instructions:
- Format as:
  Subject: ...

  Body...
- Keep the email under 200 words
- Mention 1-2 specific relevant qualifications
- Politely ask about application steps / express interest in an internship arrangement
- Professional, concise, friendly tone
- Output plain text only"""

    return _generate(prompt, api_key=api_key, max_tokens=600)


def generate_tailored_cv_sections(profile_text: str, opportunity: dict, api_key: str = None) -> str:
    """
    Returns a tailored 'Professional Summary' + reordered/highlighted
    'Key Skills & Experience' bullet points the user can paste into their
    CV template for this specific opportunity.
    """
    prompt = f"""Based on the applicant's existing CV/background below, produce a TAILORED
CV section for the specific opportunity described. Do not fabricate new
experience - only reorganize, rephrase, and emphasize what's already there.

APPLICANT BACKGROUND:
{profile_text[:6000]}

OPPORTUNITY DETAILS:
Title: {opportunity.get('title')}
Organization: {opportunity.get('organization')}
Field: {opportunity.get('field')}
Summary: {opportunity.get('summary')}

Output the following sections in plain text:

PROFESSIONAL SUMMARY (3-4 sentences tailored to this opportunity)

KEY SKILLS (bullet list, most relevant to this opportunity first)

RELEVANT EXPERIENCE & PROJECTS (bullet list, rephrased to emphasize relevance to this opportunity)

Output plain text only, ready to paste into a CV template."""

    return _generate(prompt, api_key=api_key, max_tokens=1200)
