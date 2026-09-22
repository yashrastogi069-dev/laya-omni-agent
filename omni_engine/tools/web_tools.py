"""
Web Intelligence & Live Internet Toolset
- Multi-source live search (Tavily AI)
- Arbitrary URL scraping & data extraction
- REST API tester (GET/POST/JSON)
- Web file downloader
- HTTP status & latency inspector
"""

import os
import re
import urllib.request
import urllib.parse
import json

def tool_web_search(query: str, max_results: int = 6) -> str:
    """Performs deep live web search across the internet using Tavily AI."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "TAVILY_API_KEY is not configured in environment."
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        res = client.search(query=query, max_results=max_results, search_depth="advanced")
        results = res.get("results", [])
        if not results:
            return f"No results found on the live web for '{query}'."

        output = f"### Live Internet Search Results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            title = r.get("title", "No Title")
            url = r.get("url", "")
            content = r.get("content", "").strip()
            output += f"**{i}. [{title}]({url})**\n{content}\n\n"
        return output
    except Exception as e:
        return f"Web search error: {e}"


def tool_scrape_url_content(url: str) -> str:
    """Scrapes raw text, paragraphs, and headings from any live URL."""
    clean_url = url.strip().split()[0]
    if not clean_url.startswith("http"):
        clean_url = "https://" + clean_url

    try:
        req = urllib.request.Request(
            clean_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode("utf-8", errors="replace")

        # Strip scripts, styles, and extract readable text
        html = re.sub(r'<(script|style|svg|noscript)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', html)
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
        extracted = "\n\n".join(lines[:30])

        return f"### Scraped Content from `{clean_url}`:\n\n{extracted[:3500]}\n"
    except Exception as e:
        return f"Failed to scrape {clean_url}: {e}"


def tool_http_api_request(payload: str) -> str:
    """Sends a REST API request (GET/POST) and returns the JSON response.
    Format: 'GET https://api.example.com/data' or 'POST https://api.example.com/data {"key": "val"}'
    """
    parts = payload.strip().split(maxsplit=2)
    method = "GET"
    url = ""
    body = None

    if len(parts) == 1:
        url = parts[0]
    elif parts[0].upper() in ("GET", "POST", "PUT", "DELETE"):
        method = parts[0].upper()
        url = parts[1]
        if len(parts) > 2:
            body = parts[2].encode("utf-8")
    else:
        url = parts[0]

    try:
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={"User-Agent": "OmniAgent/2.0", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            status = resp.status
        return f"### HTTP {status} Response ({method} `{url}`):\n```json\n{data[:2500]}\n```"
    except Exception as e:
        return f"HTTP request failed: {e}"


def tool_download_file(payload: str) -> str:
    """Downloads a file from a URL to a local path.
    Format: 'https://example.com/file.png my_file.png'
    """
    parts = payload.strip().split()
    if not parts:
        return "Please specify URL to download."
    url = parts[0]
    filename = parts[1] if len(parts) > 1 else os.path.basename(urllib.parse.urlparse(url).path) or "downloaded_file.bin"
    dest_path = os.path.join(os.getcwd(), filename)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OmniAgent/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        size_kb = os.path.getsize(dest_path) / 1024
        return f"✅ Download complete: `{dest_path}` ({size_kb:.1f} KB)"
    except Exception as e:
        return f"Download error: {e}"
