# Modular Recon Tool Implementation Plan

This document outlines the architecture, database schema, and module design for the Python-based Modular Recon Tool. The goal is to build a highly professional, visually striking web application that features standard navigation alongside a specialized web-based CLI for executing recon tasks.

## User Review Required

> [!IMPORTANT]  
> Please review the following architectural choices and answer the open questions so we can proceed with execution.

**Open Questions:**
1. **Web Framework:** I propose using **Flask** for the backend as it integrates seamlessly with HTML/CSS frontends and Python scripts. Are you comfortable with Flask, or would you prefer FastAPI or Django?
2. **Web CLI Interactivity:** For the "Web CLI", should it be a simple command input bar with scrolling text output, or a fully emulated terminal (using something like `xterm.js`)?
3. **Database Credentials:** We will need to set up a local MySQL database. Do you already have a MySQL server running locally that we can use, or should we plan for setting one up (e.g., via Docker)?

---

## 1. System Architecture

The project will be split into three main layers:

### A. Frontend (HTML / CSS / Vanilla JS)
- **Aesthetic:** "Cyber-Professional". A sleek dark theme (slate/charcoal backgrounds) with subtle neon accents (cyan/matrix green) to give a modern hacker feel.
- **Layout:**
  - **Top/Side Navigation Bar:** Links to `Dashboard`, `New Scan`, `Results Viewer`, and `Web CLI`.
  - **Web CLI View:** A dedicated page featuring a terminal-like interface where users can type commands (e.g., `run recon -target example.com -m A,B,C`).
- **Functionality:** AJAX/Fetch API will be used to send CLI commands to the backend without reloading the page, displaying the real-time or polled output in the terminal window.

### B. Backend (Python / Flask)
- Exposes REST API endpoints for the frontend to trigger scans and retrieve results.
- Manages the execution of the recon modules (can run scans asynchronously in background threads so the web UI doesn't block).
- Handles interactions with the MySQL database.

### C. MySQL Database
To persist all recon data across sessions, we will use a relational schema.

**Proposed Tables:**
- `targets`: `id`, `domain_name`, `added_at`
- `subdomains` (Module A): `id`, `target_id`, `subdomain`, `discovered_at`
- `directories` (Module B): `id`, `subdomain_id`, `url`, `status_code`, `content_length`
- `vulnerabilities` (Module C): `id`, `directory_id`, `form_action`, `input_fields`, `suggested_payloads`

---

## 2. Core Modules Implementation

The core Python logic will be isolated from the web routes for modularity.

### Module A: Subdomain Discovery (crt.sh API)
- **Logic:** Makes an HTTP GET request to `https://crt.sh/?q=%.{target}&output=json`.
- **Processing:** Parses the JSON response, extracts the `name_value` fields, and strips out wildcards (`*`).
- **Deduplication:** Uses Python `set()` to ensure unique subdomains before saving to the database.

### Module B: Multi-threaded Directory Brute-Forcer
- **Logic:** Takes the list of subdomains from Module A.
- **Engine:** Uses `concurrent.futures.ThreadPoolExecutor` for high-speed concurrent HTTP requests.
- **Workflow:** 
  1. Loads a custom wordlist (e.g., `wordlist.txt`).
  2. Iterates over subdomains and paths.
  3. Records URLs that return status codes like `200 OK`, `403 Forbidden`, `301 Redirect`.
  4. Skips/filters out `404 Not Found`.

### Module C: Contextual Payload Suggester
- **Logic:** Takes URLs from Module B that returned a `200 OK` status.
- **Processing:** 
  1. Fetches the page HTML content.
  2. Uses `BeautifulSoup` to parse the DOM and look for `<form>` and `<input>` tags.
  3. If input forms are found, it analyzes the `name` or `type` attributes.
- **Payload Generation:** Based on the presence of forms, it generates 5 specific payloads. For example:
  - **XSS:** `"><script>alert(1)</script>`, `'onmouseover='alert(1)'`
  - **SQLi:** `' OR '1'='1`, `admin' -- `, `" OR 1=1#`

---

## 3. Web CLI Interface Design

The CLI is a core feature embedded within the website.
- **Input:** A styled `<input type="text">` styled to look like a terminal prompt (`root@recon:~# `).
- **Output:** A scrolling `<div>` that appends text.
- **Commands:** 
  - `help`: Lists available commands.
  - `scan <domain>`: Runs the full suite.
  - `show subdomains <domain>`: Fetches results from MySQL.
  - `clear`: Clears the terminal screen.

---

## 4. Verification Plan

1. **Backend Testing:** Run each Python module independently from the command line to ensure they work before attaching them to Flask.
2. **Module A:** Test against a known bug bounty target to verify JSON parsing from crt.sh.
3. **Module B:** Spin up a local Python dummy server (`python -m http.server`) with fake directories and run the brute-forcer against it to ensure threading works safely.
4. **Module C:** Create a dummy HTML page with various forms (login, search) and verify that the BeautifulSoup logic correctly identifies them and suggests relevant payloads.
5. **Database Testing:** Perform end-to-end flow and verify data appears correctly in MySQL.
6. **UI Testing:** Ensure the Web CLI feels responsive and the navigation bar works correctly across pages.
