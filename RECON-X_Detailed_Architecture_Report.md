# RECON-X Architecture & Technical Report

A fully detailed overview of logic, background processes, and information sources.

## 1. System Overview
RECON-X is a modular reconnaissance platform designed for security researchers and pentesters. The application is built using Python, Flask, and MySQL for persistent storage. It features a robust, role-based authentication system, real-time background scanning, and dynamic payload suggestions. The architecture is explicitly designed to handle long-running, multi-threaded network operations without blocking the main web server threads.

## 2. Module A — Subdomain Discovery
**Background Logic:**
Module A is responsible for finding valid subdomains for a given target. It operates using a concurrent ThreadPoolExecutor to query multiple external APIs simultaneously. This parallel execution prevents the entire scan from hanging if a single API times out. Once responses are received, the logic extracts hostnames, strips wildcard prefixes (e.g., `*.`), ensures the domains end with the target domain name, and aggregates them into a unique Set data structure to automatically remove duplicates.

**Information Sources Used:**
* **crt.sh (Certificate Transparency):** Queries historical SSL/TLS certificate issuance logs.
* **HackerTarget (Host Search):** A public API aggregating forward/reverse DNS lookups.
* **AlienVault OTX (Passive DNS):** Leverages the Open Threat Exchange's massive repository of passive DNS records.
* **CertSpotter (Issuance Logs):** Additional certificate transparency logging source to cover gaps in crt.sh.

## 3. Module B — Directory Brute-forcing
**Background Logic:**
This module takes the subdomains discovered in Module A and attempts to find hidden directories or files. It uses a high-concurrency ThreadPoolExecutor (typically 20-50 threads) to aggressively issue HTTP GET requests. The underlying logic checks the HTTP Status Code of each response. It purposefully ignores 404 (Not Found) errors, but captures and logs interesting status codes such as 200 (OK), 301/302 (Redirects), and 403 (Forbidden), along with the Content-Length of the response payload to help identify interesting endpoints.

**Information Sources Used:**
* A local flat-file text wordlist (typically `wordlists/common.txt`) containing thousands of common administrative paths, backup file extensions, and hidden directories.

## 4. Module C — Contextual Vulnerability Payload Suggester
**Background Logic:**
Module C takes all the "200 OK" URLs discovered by Module B and fetches their full HTML source code. It utilizes the BeautifulSoup library to parse the HTML DOM specifically hunting for `<form>` elements and their corresponding input tags. The core logic examines the `name` or `id` attributes of these inputs (e.g., "search", "username", "email") and intelligently maps them to a contextual attack vector. For example, "search" fields are mapped to Cross-Site Scripting (XSS) payloads, while "username" or "password" fields are mapped to SQL Injection (SQLi) payloads.

**Information Sources Used:**
* In-memory curated Python lists of highly effective, modern XSS and SQLi payloads, optimized for bypassing basic filters.

## 5. Background Execution Engine & Threading
**Background Logic:**
To ensure the Flask web UI remains responsive, scans cannot be executed synchronously on the main thread. When a user clicks "Launch Scan", an API call is made to `/api/scan/start`. The backend instantiates a dedicated native OS thread (using Python's `threading.Thread`) to run the sequence of Modules A, B, and C. A `threading.Event` flag is passed to the thread, allowing the user to gracefully terminate the running scan from the UI. The thread continuously emits real-time textual logs into an in-memory dictionary. The front-end Javascript subsequently polls the `/api/scan/<id>/detail` endpoint every few seconds to fetch these logs and update the live web terminal interface.

## 6. Authentication & Data Scoping
**Background Logic:**
RECON-X utilizes standard server-side Flask sessions utilizing cryptographically signed cookies. User passwords are one-way hashed using SHA-256 before being stored. The application enforces a strict Multi-Tenant data isolation policy. Every scan result stored in the MySQL database includes a `scanned_by` column tracking the owner. Regular users querying the database are restricted at the SQL level to only retrieve records matching their own username. The hardcoded "Admin" account bypasses this restriction and is granted global visibility across all scans.
