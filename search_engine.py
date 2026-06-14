"""
search_engine.py
Performs real-time web searches for internships, fellowships, research
positions and lab/company contacts relevant to chemical engineering.

This module uses DuckDuckGo's HTML search endpoint via plain `requests` +
`BeautifulSoup` (no heavy/compiled dependencies, so it installs instantly
on Streamlit Cloud).

IMPORTANT NOTE ON SOCIAL MEDIA:
LinkedIn, X (Twitter), Instagram and Facebook do not allow automated
scraping of their pages (this breaks their Terms of Service and is
technically blocked for logged-out clients). The legal and reliable way to
surface opportunities posted on those platforms is to search the public web
for pages indexed from those sites using "site:" filters - which is exactly
what this module does. Results that come from those domains will be clearly
labeled with their source platform.
"""

import time
import random
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://html.duckduckgo.com/html/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

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

        for src in random.sample(GENERAL_SOURCES, 2):
            queries.append(f"{q} {src}")

    if include_social:
        for label, site_filter in SOCIAL_SITES.items():
            q = f"{field} internship fellowship {site_filter}"
            if place and place.lower() != "anywhere":
                q += f" {place}"
            queries.append(q)

    return queries


def _clean_ddg_link(href: str) -> str:
    """DuckDuckGo HTML results wrap real URLs like /l/?uddg=<encoded_url>."""
    if not href:
        return href
    if href.startswith("//"):
        href = "https:" + href
    if "duckduckgo.com/l/" in href or href.startswith("/l/"):
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def _run_single_query(query: str, results_per_query: int = 6) -> list:
    """Run one query against DuckDuckGo's HTML endpoint and parse results."""
    results = []
    try:
        resp = requests.post(
            SEARCH_URL,
            data={"q": query},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result")[:results_per_query]:
            title_tag = result.select_one(".result__title a")
            snippet_tag = result.select_one(".result__snippet")
            if not title_tag:
                continue

            link = _clean_ddg_link(title_tag.get("href", ""))
            title = title_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            if not link:
                continue

            results.append({
                "title": title,
                "link": link,
                "snippet": snippet,
            })
    except Exception as e:
        results.append({
            "title": f"[Search error for query: {query}]",
            "link": "",
            "snippet": str(e),
            "error": True,
        })
    return results


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

    for q in queries:
        raw_results = _run_single_query(q, results_per_query=results_per_query)

        for r in raw_results:
            if r.get("error"):
                results.append({
                    "title": r["title"],
                    "link": "",
                    "snippet": r["snippet"],
                    "source": "Error",
                    "query": q,
                })
                continue

            link = r["link"]
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            # Determine which "platform" this came from for labeling
            source = "Web"
            link_lower = link.lower()
            if "linkedin.com" in link_lower:
                source = "LinkedIn"
            elif "x.com" in link_lower or "twitter.com" in link_lower:
                source = "X / Twitter"
            elif "instagram.com" in link_lower:
                source = "Instagram"
            elif "facebook.com" in link_lower:
                source = "Facebook"

            results.append({
                "title": r["title"] or "Untitled",
                "link": link,
                "snippet": r["snippet"],
                "source": source,
                "query": q,
            })

        time.sleep(0.5)  # be polite / avoid rate-limiting

    return results
