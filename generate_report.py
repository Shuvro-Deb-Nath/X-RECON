from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor

def create_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor("#7b2ff7"),
        spaceAfter=20,
        alignment=TA_LEFT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor("#00f5d4"),
        spaceBefore=15,
        spaceAfter=10
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=HexColor("#111827"),
        spaceBefore=10,
        spaceAfter=5
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        leftIndent=20,
        spaceAfter=5
    )

    story = []
    
    # Title
    story.append(Paragraph("RECON-X Architecture & Technical Report", title_style))
    story.append(Paragraph("A fully detailed overview of logic, background processes, and information sources.", body_style))
    story.append(Spacer(1, 20))
    
    # Section 1: Overview
    story.append(Paragraph("1. System Overview", heading_style))
    story.append(Paragraph("RECON-X is a modular reconnaissance platform designed for security researchers and pentesters. The application is built using Python, Flask, and MySQL for persistent storage. It features a robust, role-based authentication system, real-time background scanning, and dynamic payload suggestions. The architecture is explicitly designed to handle long-running, multi-threaded network operations without blocking the main web server threads.", body_style))
    
    # Section 2: Module A
    story.append(Paragraph("2. Module A — Subdomain Discovery", heading_style))
    story.append(Paragraph("Background Logic:", subheading_style))
    story.append(Paragraph("Module A is responsible for finding valid subdomains for a given target. It operates using a concurrent ThreadPoolExecutor to query multiple external APIs simultaneously. This parallel execution prevents the entire scan from hanging if a single API times out. Once responses are received, the logic extracts hostnames, strips wildcard prefixes (e.g., '*.' ), ensures the domains end with the target domain name, and aggregates them into a unique Set data structure to automatically remove duplicates.", body_style))
    story.append(Paragraph("Information Sources Used:", subheading_style))
    
    sources_a = [
        Paragraph("<b>crt.sh (Certificate Transparency):</b> Queries historical SSL/TLS certificate issuance logs.", bullet_style),
        Paragraph("<b>HackerTarget (Host Search):</b> A public API aggregating forward/reverse DNS lookups.", bullet_style),
        Paragraph("<b>AlienVault OTX (Passive DNS):</b> Leverages the Open Threat Exchange's massive repository of passive DNS records.", bullet_style),
        Paragraph("<b>CertSpotter (Issuance Logs):</b> Additional certificate transparency logging source to cover gaps in crt.sh.", bullet_style)
    ]
    story.append(ListFlowable([ListItem(p) for p in sources_a], bulletType='bullet'))
    
    # Section 3: Module B
    story.append(Paragraph("3. Module B — Directory Brute-forcing", heading_style))
    story.append(Paragraph("Background Logic:", subheading_style))
    story.append(Paragraph("This module takes the subdomains discovered in Module A and attempts to find hidden directories or files. It uses a high-concurrency ThreadPoolExecutor (typically 20-50 threads) to aggressively issue HTTP GET requests. The underlying logic checks the HTTP Status Code of each response. It purposefully ignores 404 (Not Found) errors, but captures and logs interesting status codes such as 200 (OK), 301/302 (Redirects), and 403 (Forbidden), along with the Content-Length of the response payload to help identify interesting endpoints.", body_style))
    story.append(Paragraph("Information Sources Used:", subheading_style))
    story.append(Paragraph("A local flat-file text wordlist (typically 'wordlists/common.txt') containing thousands of common administrative paths, backup file extensions, and hidden directories.", bullet_style))

    # Section 4: Module C
    story.append(Paragraph("4. Module C — Contextual Vulnerability Payload Suggester", heading_style))
    story.append(Paragraph("Background Logic:", subheading_style))
    story.append(Paragraph("Module C takes all the '200 OK' URLs discovered by Module B and fetches their full HTML source code. It utilizes the BeautifulSoup library to parse the HTML DOM specifically hunting for '&lt;form&gt;' elements and their corresponding input tags. The core logic examines the 'name' or 'id' attributes of these inputs (e.g., 'search', 'username', 'email') and intelligently maps them to a contextual attack vector. For example, 'search' fields are mapped to Cross-Site Scripting (XSS) payloads, while 'username' or 'password' fields are mapped to SQL Injection (SQLi) payloads.", body_style))
    story.append(Paragraph("Information Sources Used:", subheading_style))
    story.append(Paragraph("In-memory curated Python lists of highly effective, modern XSS and SQLi payloads, optimized for bypassing basic filters.", bullet_style))

    # Section 5: Background Engine
    story.append(Paragraph("5. Background Execution Engine & Threading", heading_style))
    story.append(Paragraph("Background Logic:", subheading_style))
    story.append(Paragraph("To ensure the Flask web UI remains responsive, scans cannot be executed synchronously on the main thread. When a user clicks 'Launch Scan', an API call is made to '/api/scan/start'. The backend instantiates a dedicated native OS thread (using Python's 'threading.Thread') to run the sequence of Modules A, B, and C. A 'threading.Event' flag is passed to the thread, allowing the user to gracefully terminate the running scan from the UI. The thread continuously emits real-time textual logs into an in-memory dictionary. The front-end Javascript subsequently polls the '/api/scan/&lt;id&gt;/detail' endpoint every few seconds to fetch these logs and update the live web terminal interface.", body_style))

    # Section 6: Authentication & Authorization
    story.append(Paragraph("6. Authentication & Data Scoping", heading_style))
    story.append(Paragraph("Background Logic:", subheading_style))
    story.append(Paragraph("RECON-X utilizes standard server-side Flask sessions utilizing cryptographically signed cookies. User passwords are one-way hashed using SHA-256 before being stored. The application enforces a strict Multi-Tenant data isolation policy. Every scan result stored in the MySQL database includes a 'scanned_by' column tracking the owner. Regular users querying the database are restricted at the SQL level to only retrieve records matching their own username. The hardcoded 'Admin' account bypasses this restriction and is granted global visibility across all scans.", body_style))

    doc.build(story)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_pdf("RECON-X_Detailed_Architecture_Report.pdf")
