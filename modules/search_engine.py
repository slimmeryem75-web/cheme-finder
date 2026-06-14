"""
search_engine.py
Performs real-time web searches for internships, fellowships, research
positions and lab/company contacts relevant to chemical engineering.

Uses DuckDuckGo with two strategies:
  1. JSON API (instant, no scraping, works on Streamlit Cloud)
  2. HTML scraping fallback (if JSON returns nothing)
"""

import time
import random
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

DDG_JSON_URL = "https://api.duckduckgo.com/"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

SOCIAL_SITES = {
    "LinkedIn":    "site:linkedin.com",
    "X / Twitter": "site:x.com OR site:twitter.com",
    "Instagram":   "site:instagram.com",
    "Facebook":    "site:facebook.com",
}

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


def _build_queries(field, place, degree, funding, duration, period, include_social):
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


def _query_ddg_json(query: str, max_results: int = 6) -> list:
    """
    Primary method: DuckDuckGo instant-answer JSON API.
    Works reliably on Streamlit Cloud without scraping.
    Returns a list of {title, link, snippet} dicts.
    """
    results = []
    try:
        resp = requests.get(
            DDG_JSON_URL,
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # RelatedTopics contains the most useful links
        for topic in data.get("RelatedTopics", []):
            if len(results) >= max_results:
                break
            # Topics can be flat or nested under "Topics"
            items = topic.get("Topics", [topic])
            for item in items:
                if len(results) >= max_results:
                    break
                url = item.get("FirstURL", "")
                text = item.get("Text", "")
                if url and text:
                    results.append({"title": text[:120], "link": url, "snippet": text})

        # AbstractURL is another good source
        if data.get("AbstractURL") and data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "link": data["AbstractURL"],
                "snippet": data["AbstractText"],
            })

    except Exception as e:
        print(f"[search_engine] DDG JSON error for '{query}': {e}")

    return results


def _query_ddg_html(query: str, max_results: int = 6) -> list:
    """
    Fallback method: DuckDuckGo HTML scraping.
    More results but may be rate-limited on cloud deployments.
    """
    results = []
    try:
        resp = requests.post(
            DDG_HTML_URL,
            data={"q": query},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result")[:max_results]:
            title_tag = result.select_one(".result__title a")
            snippet_tag = result.select_one(".result__snippet")
            if not title_tag:
                continue
            link = _clean_ddg_link(title_tag.get("href", ""))
            title = title_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if link:
                results.append({"title": title, "link": link, "snippet": snippet})

    except Exception as e:
        print(f"[search_engine] DDG HTML error for '{query}': {e}")

    return results


def _run_single_query(query: str, results_per_query: int = 6) -> list:
    """Try JSON API first, fall back to HTML scraping."""
    results = _query_ddg_json(query, max_results=results_per_query)

    if not results:
        print(f"[search_engine] JSON returned nothing for '{query}', trying HTML scrape...")
        results = _query_ddg_html(query, max_results=results_per_query)

    if not results:
        print(f"[search_engine] Both methods returned nothing for: '{query}'")

    return results


def _source_label(link: str) -> str:
    ll = link.lower()
    if "linkedin.com" in ll:   return "LinkedIn"
    if "x.com" in ll or "twitter.com" in ll: return "X / Twitter"
    if "instagram.com" in ll:  return "Instagram"
    if "facebook.com" in ll:   return "Facebook"
    if "indeed.com" in ll:     return "Indeed"
    if "glassdoor.com" in ll:  return "Glassdoor"
    if "findaphd.com" in ll:   return "FindAPhD"
    if "euraxess" in ll:       return "EURAXESS"
    if "aiche.org" in ll:      return "AIChE"
    if "acs.org" in ll:        return "ACS"
    return "Web"


def search_opportunities(field, place, degree, funding, duration, period,
                          include_social=True, max_queries=8,
                          results_per_query=6, seed=None) -> list:
    queries = _build_queries(field, place, degree, funding, duration, period, include_social)

    rnd = random.Random(seed)
    rnd.shuffle(queries)
    queries = queries[:max_queries]

    print(f"[search_engine] Running {len(queries)} queries...")

    results = []
    seen_links = set()

    for q in queries:
        raw = _run_single_query(q, results_per_query=results_per_query)
        for r in raw:
            link = r.get("link", "")
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            results.append({
                "title":   r.get("title") or "Untitled",
                "link":    link,
                "snippet": r.get("snippet", ""),
                "source":  _source_label(link),
                "query":   q,
            })
        time.sleep(0.4)

    print(f"[search_engine] Total raw results collected: {len(results)}")
    return results
