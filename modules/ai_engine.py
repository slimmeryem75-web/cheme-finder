"""
ai_engine.py
Uses Groq API (100% free, no credit card) with Llama 3.
Get your free key at https://console.groq.com
Works on Streamlit Cloud with no restrictions.
"""

import json
import os
import re
import requests

API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def _generate(prompt: str, api_key: str = None, max_tokens: int = 1500) -> str:
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise ValueError("No Groq API key provided. Get a free key at https://console.groq.com")

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # Lower temp = more reliable JSON output
        },
        timeout=60,
    )

    # Raise a clear error so it surfaces in the UI
    if response.status_code == 401:
        raise ValueError("Invalid Groq API key. Check it at https://console.groq.com")
    if response.status_code == 429:
        raise ValueError("Groq rate limit hit. Wait a moment and try again.")
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


def _extract_json_array(text: str) -> list:
    """Try multiple strategies to extract a JSON array from LLM output."""
    # Strategy 1: markdown code fence
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Strategy 2: find outermost [ ... ]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            # Strategy 3: try to fix truncated JSON by closing open brackets
            fixed = candidate.rstrip().rstrip(",")
            # Count unclosed braces
            open_braces = fixed.count("{") - fixed.count("}")
            if open_braces > 0:
                fixed += "}" * open_braces
            fixed += "]"
            try:
                parsed = json.loads(fixed)
                if isinstance(parsed, list):
                    print("[ai_engine] Recovered truncated JSON")
                    return parsed
            except json.JSONDecodeError:
                pass

    # Strategy 4: dict wrapper
    start_d = text.find("{")
    end_d = text.rfind("}")
    if start_d != -1 and end_d != -1 and end_d > start_d:
        try:
            parsed = json.loads(text[start_d:end_d + 1])
            if isinstance(parsed, dict):
                for key in ("opportunities", "results", "data", "items"):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]
        except json.JSONDecodeError:
            pass

    return []


def structure_opportunities(raw_results: list, field: str, api_key: str = None) -> list:
    if not raw_results:
        return []

    structured = []
    chunk_size = 6  # Smaller chunks = more reliable JSON from LLM

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

        prompt = f"""You are a JSON-only API. Output ONLY a valid JSON array, nothing else.
No markdown, no explanation, no preamble. Start your response with [ and end with ].

Task: Extract structured opportunity data from the web search results below.

For each RELEVANT result (internships, fellowships, PhD/research positions for
chemical engineers / materials science / process engineering / biotech / energy),
return a JSON object with exactly these keys:
- "title": short opportunity title
- "organization": company, university, or lab name
- "location": city/country or "Remote" or "Not specified"
- "deadline": deadline if mentioned, else "Not specified"
- "period": e.g. "Summer 2026" or "Not specified"
- "duration": e.g. "3 months" or "Not specified"
- "funding": one of ["Fully Funded", "Partially Funded", "Stipend", "Unfunded", "Not specified"]
- "degree_level": one of ["Undergraduate", "Master", "PhD", "Postdoc", "Any", "Not specified"]
- "field": specific sub-field e.g. "Process Engineering"
- "contact": email or name if mentioned, else "Not specified"
- "source": the source platform as given
- "link": the link as given (do not change it)
- "summary": 1-2 sentence plain-language summary

Discard irrelevant results. If nothing is relevant, return [].

Search field: {field}

Results:
{listing_text}

Remember: output ONLY the JSON array. Start with ["""

        try:
            text = _generate(prompt, api_key=api_key, max_tokens=2500).strip()
        except ValueError as e:
            # Key/auth errors — stop immediately and surface the error
            raise
        except Exception as e:
            print(f"[ai_engine] API error on chunk {i}: {e}")
            continue

        print(f"[ai_engine] Raw response (chunk {i}, first 400 chars): {text[:400]}")

        items = _extract_json_array(text)
        if items:
            print(f"[ai_engine] Parsed {len(items)} opportunities from chunk {i}")
            structured.extend(items)
        else:
            print(f"[ai_engine] Could not parse JSON from chunk {i}. Full text:\n{text[:800]}")

    return structured


def generate_motivation_letter(profile_text: str, opportunity: dict, api_key: str = None) -> str:
    prompt = f"""Write a personalized, professional motivation letter for the following opportunity,
written in first person as the applicant.

APPLICANT PROFILE:
{profile_text[:4000]}

OPPORTUNITY DETAILS:
Title: {opportunity.get('title')}
Organization: {opportunity.get('organization')}
Location: {opportunity.get('location')}
Field: {opportunity.get('field')}
Degree level: {opportunity.get('degree_level')}
Summary: {opportunity.get('summary')}

Instructions:
- 350-450 words
- Base the letter on what the applicant has shared about themselves
- Connect their stated interests and goals to what this specific opportunity offers
- Professional but warm and genuine tone
- Structure: strong opening paragraph, 2 body paragraphs, closing with call to action
- Do not fabricate specific achievements not mentioned in the profile
- Output plain text only, ready to copy into a document"""

    return _generate(prompt, api_key=api_key, max_tokens=1200)


def generate_email(profile_text: str, opportunity: dict, api_key: str = None) -> str:
    prompt = f"""Write a short, polite, personalized outreach email (with subject line) to inquire
about or apply for the following opportunity.

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
- Politely ask about application steps / express interest
- Professional, concise, friendly tone
- Output plain text only"""

    return _generate(prompt, api_key=api_key, max_tokens=600)


def generate_tailored_cv_sections(profile_text: str, opportunity: dict, api_key: str = None) -> str:
    prompt = f"""Based on the applicant's existing CV/background below, produce a TAILORED
CV section for the specific opportunity. Do not fabricate new experience.

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

RELEVANT EXPERIENCE & PROJECTS (bullet list, rephrased to emphasize relevance)

Output plain text only, ready to paste into a CV template."""

    return _generate(prompt, api_key=api_key, max_tokens=1200)
