"""
Module A — Subdomain Discovery via multiple sources
"""
import requests
import re
import concurrent.futures

HEADERS = {"User-Agent": "ReconX/1.0 (security research)"}


def query_crtsh(domain: str, log_fn) -> set[str]:
    subs = set()
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            try:
                data = resp.json()
                for entry in data:
                    names = entry.get("name_value", "")
                    for name in names.splitlines():
                        name = name.strip().lower()
                        name = re.sub(r"^\*\.", "", name)
                        if name.endswith(domain) and "*" not in name:
                            subs.add(name)
            except ValueError:
                pass
        log_fn(f"[crt.sh] Found {len(subs)} subdomains")
    except Exception as e:
        log_fn(f"[crt.sh] Error: {e}")
    return subs


def query_hackertarget(domain: str, log_fn) -> set[str]:
    subs = set()
    try:
        url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                if "," in line:
                    name = line.split(",")[0].strip().lower()
                    if name.endswith(domain):
                        subs.add(name)
        log_fn(f"[hackertarget] Found {len(subs)} subdomains")
    except Exception as e:
        log_fn(f"[hackertarget] Error: {e}")
    return subs


def query_alienvault(domain: str, log_fn) -> set[str]:
    subs = set()
    try:
        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for entry in data.get("passive_dns", []):
                name = entry.get("hostname", "").strip().lower()
                if name.endswith(domain) and "*" not in name:
                    subs.add(name)
        log_fn(f"[alienvault] Found {len(subs)} subdomains")
    except Exception as e:
        log_fn(f"[alienvault] Error: {e}")
    return subs


def query_certspotter(domain: str, log_fn) -> set[str]:
    subs = set()
    try:
        url = f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for entry in data:
                for name in entry.get("dns_names", []):
                    name = name.strip().lower()
                    name = re.sub(r"^\*\.", "", name)
                    if name.endswith(domain) and "*" not in name:
                        subs.add(name)
        log_fn(f"[certspotter] Found {len(subs)} subdomains")
    except Exception as e:
        log_fn(f"[certspotter] Error: {e}")
    return subs


def run(domain: str, log_fn=print) -> list[str]:
    """
    Query multiple sources to discover unique subdomains for *domain*.
    """
    log_fn(f"[MODULE A] Starting subdomain discovery for: {domain}")
    
    subdomains: set[str] = set()
    
    # Run queries concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(query_crtsh, domain, log_fn),
            executor.submit(query_hackertarget, domain, log_fn),
            executor.submit(query_alienvault, domain, log_fn),
            executor.submit(query_certspotter, domain, log_fn)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                subs = future.result()
                subdomains.update(subs)
            except Exception as e:
                log_fn(f"[MODULE A] Unexpected thread error: {e}")
    
    result = sorted(subdomains)
    log_fn(f"[MODULE A] Discovered {len(result)} unique subdomain(s) across all sources")
    for s in result:
        log_fn(f"  └─ {s}")
    return result


