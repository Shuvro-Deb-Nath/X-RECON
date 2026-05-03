"""
Database layer — MySQL connection and CRUD helpers
"""
import json
import mysql.connector
from mysql.connector import Error
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


# ── Schema DDL ─────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    email         VARCHAR(255),
    password_hash VARCHAR(64)  NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'user',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS targets (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    domain     VARCHAR(255) NOT NULL,
    scanned_by VARCHAR(100) NOT NULL DEFAULT 'unknown',
    added_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subdomains (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    target_id     INT NOT NULL,
    subdomain     VARCHAR(255) NOT NULL,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS directories (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    subdomain_id   INT NOT NULL,
    url            TEXT NOT NULL,
    status_code    INT,
    content_length INT,
    scanned_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subdomain_id) REFERENCES subdomains(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vulnerabilities (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    directory_id    INT NOT NULL,
    form_action     TEXT,
    method          VARCHAR(10),
    input_fields    TEXT,
    payload_type    VARCHAR(50),
    suggested_payloads TEXT,
    found_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (directory_id) REFERENCES directories(id) ON DELETE CASCADE
);
"""


def get_connection():
    """Return a fresh MySQL connection."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
    )


def init_db():
    """Create the database if absent and run schema DDL."""
    # First connect without selecting a database to create it if needed
    conn = mysql.connector.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        autocommit=True,
    )
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE {DB_NAME}")
    for stmt in SCHEMA_SQL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.close()


# ── User helpers ──────────────────────────────────────────────────────────────

def user_exists(username: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def create_user(username: str, password_hash: str, email: str = "", role: str = "user"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
        (username, email or None, password_hash, role)
    )
    conn.close()


def get_user(username: str) -> dict | None:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    row = cur.fetchone()
    conn.close()
    return row


# ── Target helpers ─────────────────────────────────────────────────────────────

def upsert_target(domain: str, scanned_by: str = "unknown") -> int:
    """Insert a new scan record (domain + who scanned it) and return its id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO targets (domain, scanned_by) VALUES (%s, %s)",
        (domain, scanned_by)
    )
    target_id = cur.lastrowid
    conn.close()
    return target_id


def get_all_targets():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM targets ORDER BY added_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_target(target_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM targets WHERE id=%s", (target_id,))
    conn.close()


# ── Subdomain helpers ──────────────────────────────────────────────────────────

def save_subdomains(target_id: int, subdomains: list[str]) -> dict[str, int]:
    """Save subdomains and return a mapping of subdomain → id."""
    conn = get_connection()
    cur = conn.cursor()
    mapping: dict[str, int] = {}
    for sub in subdomains:
        cur.execute(
            "INSERT INTO subdomains (target_id, subdomain) VALUES (%s, %s)",
            (target_id, sub)
        )
        mapping[sub] = cur.lastrowid
    conn.close()
    return mapping


def get_subdomains(target_id: int):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM subdomains WHERE target_id=%s ORDER BY discovered_at DESC",
        (target_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ── Directory helpers ──────────────────────────────────────────────────────────

def save_directories(subdomain_id: int, dirs: list[dict]) -> dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    mapping: dict[str, int] = {}
    for d in dirs:
        cur.execute(
            "INSERT INTO directories (subdomain_id, url, status_code, content_length) "
            "VALUES (%s, %s, %s, %s)",
            (subdomain_id, d["url"], d["status_code"], d["content_length"])
        )
        mapping[d["url"]] = cur.lastrowid
    conn.close()
    return mapping


def get_directories(subdomain_id: int):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM directories WHERE subdomain_id=%s ORDER BY status_code",
        (subdomain_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ── Vulnerability helpers ──────────────────────────────────────────────────────

def save_vulnerabilities(dir_map: dict[str, int], vulns: list[dict]):
    conn = get_connection()
    cur = conn.cursor()
    for v in vulns:
        dir_id = dir_map.get(v["url"])
        if dir_id is None:
            continue
        cur.execute(
            "INSERT INTO vulnerabilities "
            "(directory_id, form_action, method, input_fields, payload_type, suggested_payloads) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                dir_id,
                v.get("form_action", ""),
                v.get("method", ""),
                json.dumps(v.get("inputs", [])),
                v.get("payload_type", ""),
                json.dumps(v.get("payloads", [])),
            )
        )
    conn.close()


def get_all_results(username: str = None):
    """Aggregate view for the Results page. Pass username to filter by owner."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if username:
        cur.execute("""
            SELECT
                t.id,
                t.domain,
                t.scanned_by,
                COUNT(DISTINCT s.id)  AS subdomain_count,
                COUNT(DISTINCT d.id)  AS directory_count,
                COUNT(DISTINCT v.id)  AS vuln_count,
                t.added_at
            FROM targets t
            LEFT JOIN subdomains s  ON s.target_id = t.id
            LEFT JOIN directories d ON d.subdomain_id = s.id
            LEFT JOIN vulnerabilities v ON v.directory_id = d.id
            WHERE t.scanned_by = %s
            GROUP BY t.id
            ORDER BY t.added_at DESC
        """, (username,))
    else:
        cur.execute("""
            SELECT
                t.id,
                t.domain,
                t.scanned_by,
                COUNT(DISTINCT s.id)  AS subdomain_count,
                COUNT(DISTINCT d.id)  AS directory_count,
                COUNT(DISTINCT v.id)  AS vuln_count,
                t.added_at
            FROM targets t
            LEFT JOIN subdomains s  ON s.target_id = t.id
            LEFT JOIN directories d ON d.subdomain_id = s.id
            LEFT JOIN vulnerabilities v ON v.directory_id = d.id
            GROUP BY t.id
            ORDER BY t.added_at DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_target_detail(domain: str):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM targets WHERE domain=%s", (domain,))
    target = cur.fetchone()
    if not target:
        conn.close()
        return None

    cur.execute("SELECT * FROM subdomains WHERE target_id=%s", (target["id"],))
    subs = cur.fetchall()
    for sub in subs:
        cur.execute("SELECT * FROM directories WHERE subdomain_id=%s", (sub["id"],))
        dirs = cur.fetchall()
        for d in dirs:
            cur.execute("SELECT * FROM vulnerabilities WHERE directory_id=%s", (d["id"],))
            vulns = cur.fetchall()
            for v in vulns:
                v["input_fields"] = json.loads(v["input_fields"] or "[]")
                v["suggested_payloads"] = json.loads(v["suggested_payloads"] or "[]")
            d["vulnerabilities"] = vulns
        sub["directories"] = dirs
    target["subdomains"] = subs
    conn.close()
    return target
