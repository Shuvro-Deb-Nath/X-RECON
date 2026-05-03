"""
Module B — Multi-threaded Directory Brute-Forcer
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import DEFAULT_THREADS, REQUEST_TIMEOUT, INTERESTING_CODES

HEADERS = {"User-Agent": "ReconX/1.0 (security research)"}


def _probe(url: str) -> dict | None:
    """Probe a single URL and return a result dict or None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                            allow_redirects=True)
        if resp.status_code not in [404]:
            return {
                "url": url,
                "status_code": resp.status_code,
                "content_length": len(resp.content),
            }
    except requests.exceptions.RequestException:
        pass
    return None


def run(subdomains: list[str], wordlist_path: str, threads: int = DEFAULT_THREADS,
        log_fn=print, stop_event=None) -> list[dict]:
    """
    Brute-force directories on each subdomain using the supplied wordlist.

    Args:
        subdomains:    List of subdomains to probe.
        wordlist_path: Path to newline-separated wordlist file.
        threads:       Thread-pool concurrency limit.
        log_fn:        Callable for progress logging.

    Returns:
        List of dicts {url, status_code, content_length}.
    """
    log_fn(f"[MODULE B] Loading wordlist from: {wordlist_path}")
    try:
        with open(wordlist_path, "r", encoding="utf-8") as fh:
            paths = [line.strip() for line in fh if line.strip()]
    except FileNotFoundError:
        log_fn(f"[MODULE B] ERROR: Wordlist not found at {wordlist_path}")
        return []

    log_fn(f"[MODULE B] {len(paths)} paths × {len(subdomains)} subdomain(s) "
           f"= {len(paths) * len(subdomains)} probes  (threads={threads})")

    targets: list[str] = []
    for sub in subdomains:
        base = sub if sub.startswith("http") else f"http://{sub}"
        for path in paths:
            path = path.lstrip("/")
            targets.append(f"{base}/{path}")

    results: list[dict] = []
    done = 0

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {pool.submit(_probe, url): url for url in targets}
        for fut in as_completed(futures):
            # Honour stop signal — cancel remaining futures
            if stop_event and stop_event.is_set():
                for f in futures:
                    f.cancel()
                log_fn("[MODULE B] ⚠ Scan stopped by user — aborting directory brute-force")
                break
            done += 1
            result = fut.result()
            if result:
                status = result["status_code"]
                tag = ("✓" if status == 200 else
                       "⚠" if status in [301, 302] else
                       "✗")
                log_fn(f"  {tag} [{status}] {result['url']} "
                       f"({result['content_length']} bytes)")
                results.append(result)
            if done % 50 == 0:
                log_fn(f"[MODULE B] Progress: {done}/{len(targets)} probes completed")

    log_fn(f"[MODULE B] Done — {len(results)} interesting URL(s) found")
    return results

