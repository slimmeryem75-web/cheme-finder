"""
search_engine.py
Performs real-time web searches for internships, fellowships, research
positions and lab/company contacts relevant to chemical engineering.

IMPORTANT NOTE ON SOCIAL MEDIA:
LinkedIn, X (Twitter), Instagram and Facebook do not allow automated
scraping of their pages (this breaks their Terms of Service and is
technically blocked for logged-out clients). The legal and reliable way to
surface opportunities posted on those platforms is to search the public web
for pages indexed from those sites using "site:" filters - which is exactly
what this module does. Results that come from those domains will be clearly
labeled with their source platform.
"""

from duckduckgo_search import DDGS
import time
import random

# Domains we specifically search within for social/job platforms
SOCIAL_SITES = {
    "LinkedIn": "site:linkedin.com",
    "X / Twitter": "site:x.com OR site:twitter.com",
    "Instagram": "site:instagram.com",
    "Facebook": "site:facebook.com",
}

# General job / fellowship / academic boards good for chemical engineering
GENERAL_SOURCES = [
    "site:indeed.com",
    "site:glassdoor.com",
    "site:findaphd.com",
    "site:euraxess.ec.europa.eu",
    "site:academicpositions.com",
    "site:researchgate.net",
    "site:aiche.org",
    "site:acs.org",
]


def _build_queries(field: str, place: str, degree: str, funding: str,
                    duration: str, period: str, include_social: bool):
    """Construct a list of search query strings based on filters."""
    base_terms = [
        f"{field} internship",
        f"{field} fellowship",
        f"{field} research internship",
        f"{field} PhD position",
        f"{field} graduate trainee",
    ]

    # Adjust base terms for degree level
    if degree and degree != "Any":
        base_terms = [f"{t} {degree}" for t in base_terms]

    queries = []
    for term in base_terms:
        q = term
        if place and place.lower() != "anywhere":
            q += f" {place}"
        if funding and funding != "Any":
            q += f" {funding}"
        if duration and duration != "Any":
            q += f" {duration}"
        if period and period != "Any":
            q += f" {period}"
        q += " apply deadline"
        queries.append(q)

        # Add general source-restricted variants (a sample, not all, to keep it fast)
        for src in random.sample(GENERAL_SOURCES, 2):
            queries.append(f"{q} {src}")

    if include_social:
        for label, site_filter in SOCIAL_SITES.items():
            q = f"{field} internship fellowship {site_filter}"
            if place and place.lower() != "anywhere":
                q += f" {place}"
            queries.append(q)

    return queries


def search_opportunities(field: str, place: str, degree: str, funding: str,
                          duration: str, period: str,
                          include_social: bool = True,
                          max_queries: int = 8,
                          results_per_query: int = 6,
                          seed: int = None) -> list:
    """
    Run a batch of live web searches and return a deduplicated list of
    raw result dicts: {title, link, snippet, source}

    `seed` can be changed (e.g. random) each time the user presses
    the Refresh / Search button so a different slice of queries
    is used and results feel "new" each time.
    """
    queries = _build_queries(field, place, degree, funding, duration, period, include_social)

    rnd = random.Random(seed)
    rnd.shuffle(queries)
    queries = queries[:max_queries]

    results = []
    seen_links = set()

    with DDGS() as ddgs:
        for q in queries:
            try:
                for r in ddgs.text(q, max_results=results_per_query):
                    link = r.get("href") or r.get("link")
                    if not link or link in seen_links:
                        continue
                    seen_links.add(link)

                    # Determine which "platform" this came from for labeling
                    source = "Web"
                    for label, _ in SOCIAL_SITES.items():
                        domain = label.split(" / ")[0].lower().replace(" ", "")
                        if domain in link.lower() or (label == "X / Twitter" and ("x.com" in link or "twitter.com" in link)):
                            source = label
                            break

                    results.append({
                        "title": r.get("title", "Untitled"),
                        "link": link,
                        "snippet": r.get("body", ""),
                        "source": source,
                        "query": q,
                    })
            except Exception as e:
                # Continue gracefully if one query fails (rate limit, etc.)
                results.append({
                    "title": f"[Search error for query: {q}]",
                    "link": "",
                    "snippet": str(e),
                    "source": "Error",
                    "query": q,
                })
            time.sleep(0.5)  # be polite / avoid rate-limiting

    return results
