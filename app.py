"""
RECON-X  ·  Flask Application Entry Point
"""
import os
import threading
import json
from datetime import datetime
from flask import (Flask, render_template, request, jsonify,
                   Response, redirect, url_for, flash, session)
from flask_cors import CORS

# ── Bootstrap ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "recon-x-super-secret-key-2024"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
CORS(app)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
WORDLIST_PATH = os.path.join(BASE_DIR, "wordlist.txt")

# ── Database bootstrap ─────────────────────────────────────────────────────────
try:
    from database.db import (
        init_db, upsert_target, save_subdomains, save_directories,
        save_vulnerabilities, get_all_targets, get_all_results,
        get_target_detail, get_subdomains, get_directories, delete_target,
        # User helpers
        user_exists, create_user, get_user,
    )
    init_db()
    DB_AVAILABLE = True
except Exception as exc:
    print(f"[WARN] MySQL unavailable: {exc}. Running in memory-only mode.")
    DB_AVAILABLE = False

from modules import module_a, module_b, module_c
from auth import (
    login_user, logout_user, current_user, is_admin,
    login_required, attempt_login, attempt_register,
)

# ── In-memory scan registry ────────────────────────────────────────────────────
# scan_id → {status, logs, result, stop_event, scanned_by}
SCANS: dict[str, dict] = {}
SCANS_LOCK = threading.Lock()

# In-memory user scans index: username → [scan_id, ...]
USER_SCANS: dict[str, list] = {}


def new_scan_id() -> str:
    import uuid
    return uuid.uuid4().hex[:10]


# ── Auth context processor (makes current_user available in all templates) ─────

@app.context_processor
def inject_user():
    return dict(current_user=current_user(), is_admin=is_admin())


# ── Auth Pages ─────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user():
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        action = request.form.get("action", "login")
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        if action == "register":
            email = request.form.get("email", "").strip()
            ok, err = attempt_register(
                username, password, email=email,
                db_available=DB_AVAILABLE,
                db_create_user=create_user if DB_AVAILABLE else None,
                db_user_exists=user_exists if DB_AVAILABLE else None,
            )
            if ok:
                login_user(username, "user")
                return redirect(url_for("dashboard"))
            else:
                error = err
        else:
            ok, role, err = attempt_login(
                username, password,
                db_available=DB_AVAILABLE,
                db_get_user=get_user if DB_AVAILABLE else None,
            )
            if ok:
                login_user(username, role)
                return redirect(url_for("dashboard"))
            else:
                error = err

    return render_template("login.html", error=error, db=DB_AVAILABLE)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login_page"))


# ── Protected Pages ────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def dashboard():
    user = current_user()
    stats = {"targets": 0, "subdomains": 0, "directories": 0, "vulns": 0}
    recent = []

    if DB_AVAILABLE:
        # Admin sees all; others see only theirs
        if is_admin():
            targets = get_all_results()
        else:
            targets = get_all_results(username=user["username"])

        for t in targets:
            stats["targets"]    += 1
            stats["subdomains"] += t.get("subdomain_count", 0) or 0
            stats["directories"]+= t.get("directory_count", 0) or 0
            stats["vulns"]      += t.get("vuln_count", 0) or 0
        recent = targets[:5]
    else:
        # In-memory fallback
        with SCANS_LOCK:
            for sid, s in SCANS.items():
                if is_admin() or s.get("scanned_by") == user["username"]:
                    stats["targets"] += 1
                    stats["subdomains"] += len(s["result"].get("subdomains", []))
                    stats["directories"]+= len(s["result"].get("directories", []))
                    stats["vulns"]      += len(s["result"].get("vulnerabilities", []))

    return render_template("index.html", stats=stats, recent=recent,
                           db=DB_AVAILABLE, now=datetime.utcnow())


@app.route("/scan")
@login_required
def scan_page():
    return render_template("scan.html", db=DB_AVAILABLE)


@app.route("/results")
@login_required
def results_page():
    user = current_user()
    data = []
    if DB_AVAILABLE:
        if is_admin():
            data = get_all_results()
        else:
            data = get_all_results(username=user["username"])
    return render_template("results.html", data=data, db=DB_AVAILABLE)


@app.route("/results/<domain>")
@login_required
def result_detail(domain):
    detail = None
    if DB_AVAILABLE:
        detail = get_target_detail(domain)
    return render_template("detail.html", detail=detail, domain=domain, db=DB_AVAILABLE)


@app.route("/cli")
@login_required
def cli_page():
    return render_template("cli.html", db=DB_AVAILABLE)


@app.route("/favicon.ico")
def favicon():
    """Serve SVG favicon to prevent 404 errors."""
    return Response(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36">'
        '<circle cx="18" cy="18" r="16" stroke="#00f5d4" stroke-width="2" fill="none"/>'
        '<path d="M18 6 L30 24 L6 24 Z" fill="#7b2ff7" opacity="0.8"/>'
        '<circle cx="18" cy="18" r="4" fill="#00f5d4"/>'
        '</svg>',
        mimetype='image/svg+xml'
    )


# ── API — Scan Execution ───────────────────────────────────────────────────────

@app.route("/api/scan/start", methods=["POST"])
@login_required
def api_scan_start():
    user   = current_user()
    body   = request.get_json(force=True)
    domain = (body.get("domain") or "").strip().lower()
    modules = body.get("modules", ["A", "B", "C"])
    threads = int(body.get("threads", 20))
    wordlist = body.get("wordlist", WORDLIST_PATH)

    if not domain:
        return jsonify({"error": "domain is required"}), 400

    scan_id    = new_scan_id()
    stop_event = threading.Event()
    scanned_by = user["username"]

    with SCANS_LOCK:
        SCANS[scan_id] = {
            "status":     "running",
            "logs":       [],
            "result":     {},
            "stop_event": stop_event,
            "scanned_by": scanned_by,
            "domain":     domain,
        }
        USER_SCANS.setdefault(scanned_by, []).append(scan_id)

    def run_scan():
        logs = SCANS[scan_id]["logs"]

        def log(msg):
            ts    = datetime.utcnow().strftime("%H:%M:%S")
            entry = f"[{ts}] {msg}"
            logs.append(entry)

        try:
            log(f"══ RECON-X SCAN STARTED — target: {domain} ══")

            def is_stopped():
                return stop_event.is_set()

            # Module A
            subdomains = []
            if "A" in modules:
                subdomains = module_a.run(domain, log_fn=log)
            else:
                subdomains = [domain]

            if is_stopped():
                log("⚠ Scan stopped by user after Module A.")
                SCANS[scan_id]["status"] = "stopped"
                return

            sub_map: dict[str, int] = {}
            target_id = None
            if DB_AVAILABLE and subdomains:
                target_id = upsert_target(domain, scanned_by=scanned_by)
                sub_map   = save_subdomains(target_id, subdomains)

            # Module B
            dir_results = []
            dir_map: dict[str, int] = {}
            if "B" in modules and subdomains:
                dir_results = module_b.run(
                    subdomains, wordlist or WORDLIST_PATH,
                    threads=threads, log_fn=log,
                    stop_event=stop_event
                )
                if DB_AVAILABLE:
                    for d in dir_results:
                        url = d["url"]
                        for sub, sid in sub_map.items():
                            if url.startswith(f"http://{sub}") or url.startswith(f"https://{sub}"):
                                dm = save_directories(sid, [d])
                                dir_map.update(dm)
                                break

            if is_stopped():
                log("⚠ Scan stopped by user after Module B.")
                SCANS[scan_id]["result"] = {
                    "subdomains":      subdomains,
                    "directories":     dir_results,
                    "vulnerabilities": [],
                }
                SCANS[scan_id]["status"] = "stopped"
                return

            # Module C
            vuln_results = []
            if "C" in modules and dir_results:
                vuln_results = module_c.run(dir_results, log_fn=log)
                if DB_AVAILABLE and dir_map:
                    save_vulnerabilities(dir_map, vuln_results)

            SCANS[scan_id]["result"] = {
                "subdomains":      subdomains,
                "directories":     dir_results,
                "vulnerabilities": vuln_results,
            }
            SCANS[scan_id]["status"] = "done"
            log(f"══ SCAN COMPLETE — subdomains:{len(subdomains)} "
                f"dirs:{len(dir_results)} vulns:{len(vuln_results)} ══")

        except Exception as exc:
            log(f"[FATAL] {exc}")
            SCANS[scan_id]["status"] = "error"

    t = threading.Thread(target=run_scan, daemon=True)
    t.start()
    return jsonify({"scan_id": scan_id})


@app.route("/api/scan/<scan_id>/poll")
@login_required
def api_scan_poll(scan_id):
    user = current_user()
    with SCANS_LOCK:
        scan = SCANS.get(scan_id)
    if not scan:
        return jsonify({"error": "scan not found"}), 404
    # Non-admin can only poll their own scans
    if not is_admin() and scan.get("scanned_by") != user["username"]:
        return jsonify({"error": "forbidden"}), 403

    since    = int(request.args.get("since", 0))
    new_logs = scan["logs"][since:]
    done     = scan["status"] in ("done", "stopped", "error")
    return jsonify({
        "status":     scan["status"],
        "logs":       new_logs,
        "log_offset": since + len(new_logs),
        "result":     scan["result"] if done else {},
    })


@app.route("/api/scan/<scan_id>/stop", methods=["POST"])
@login_required
def api_scan_stop(scan_id):
    user = current_user()
    with SCANS_LOCK:
        scan = SCANS.get(scan_id)
    if not scan:
        return jsonify({"error": "scan not found"}), 404
    if not is_admin() and scan.get("scanned_by") != user["username"]:
        return jsonify({"error": "forbidden"}), 403
    if scan["status"] != "running":
        return jsonify({"ok": True, "status": scan["status"]})
    scan["stop_event"].set()
    return jsonify({"ok": True, "status": "stopping"})


@app.route("/api/scan/<scan_id>/detail")
@login_required
def api_scan_detail(scan_id):
    user = current_user()
    with SCANS_LOCK:
        scan = SCANS.get(scan_id)
    if not scan:
        return jsonify({"error": "scan not found"}), 404
    if not is_admin() and scan.get("scanned_by") != user["username"]:
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "scan_id":    scan_id,
        "status":     scan["status"],
        "logs":       scan["logs"],
        "result":     scan["result"],
        "scanned_by": scan.get("scanned_by", "unknown"),
        "domain":     next(
            (l.split("target: ")[-1].rstrip(" ═") for l in scan["logs"] if "target:" in l),
            "unknown"
        ),
    })


# ── API — Data Queries ─────────────────────────────────────────────────────────

@app.route("/api/scans")
@login_required
def api_scans():
    """Return in-memory scans filtered by user (admin sees all)."""
    user = current_user()
    with SCANS_LOCK:
        snapshot = []
        for sid, s in SCANS.items():
            if not is_admin() and s.get("scanned_by") != user["username"]:
                continue
            snapshot.append({
                "scan_id":         sid,
                "status":          s["status"],
                "scanned_by":      s.get("scanned_by", "unknown"),
                "domain":          (s.get("domain") or
                                    s["result"].get("domain") or
                                    next((l.split("target: ")[-1].rstrip(" ═")
                                         for l in s["logs"] if "target:" in l), "unknown")),
                "subdomain_count": len(s["result"].get("subdomains", [])),
                "directory_count": len(s["result"].get("directories", [])),
                "vuln_count":      len(s["result"].get("vulnerabilities", [])),
                "log_count":       len(s["logs"]),
                "started_at":      next(
                    (l[1:9] for l in s["logs"] if l.startswith("[")), "--:--:--"
                ),
            })
    return jsonify(snapshot)


@app.route("/api/targets")
@login_required
def api_targets():
    if not DB_AVAILABLE:
        return jsonify({"error": "database unavailable"}), 503
    user = current_user()
    if is_admin():
        return jsonify(get_all_results())
    return jsonify(get_all_results(username=user["username"]))


@app.route("/api/targets/<int:target_id>", methods=["DELETE"])
@login_required
def api_delete_target(target_id):
    if not DB_AVAILABLE:
        return jsonify({"error": "database unavailable"}), 503
    delete_target(target_id)
    return jsonify({"ok": True})


# ── API — Web CLI ──────────────────────────────────────────────────────────────

@app.route("/api/cli", methods=["POST"])
@login_required
def api_cli():
    body = request.get_json(force=True)
    cmd  = (body.get("command") or "").strip()

    def respond(lines):
        return jsonify({"output": lines})

    parts = cmd.split()
    if not parts:
        return respond([""])

    verb = parts[0].lower()

    if verb == "help":
        return respond([
            "╔══════════════════════════════════════════════════╗",
            "║              RECON-X  CLI  HELP                 ║",
            "╠══════════════════════════════════════════════════╣",
            "║  scan <domain> [-m A,B,C] [-t threads]          ║",
            "║      Start a full recon scan                     ║",
            "║  show subdomains <domain>                        ║",
            "║      List subdomains from database               ║",
            "║  show results                                    ║",
            "║      Show all scan summaries                     ║",
            "║  status <scan_id>                               ║",
            "║      Check a running scan's status               ║",
            "║  clear                                           ║",
            "║      Clear the terminal                          ║",
            "║  help                                            ║",
            "║      Show this message                           ║",
            "╚══════════════════════════════════════════════════╝",
        ])

    if verb == "clear":
        return jsonify({"clear": True})

    if verb == "scan":
        if len(parts) < 2:
            return respond(["Usage: scan <domain> [-m A,B,C] [-t threads]"])
        domain  = parts[1]
        modules = ["A", "B", "C"]
        threads = 20
        try:
            if "-m" in parts:
                idx     = parts.index("-m")
                modules = [m.upper() for m in parts[idx + 1].split(",")]
            if "-t" in parts:
                idx     = parts.index("-t")
                threads = int(parts[idx + 1])
        except (IndexError, ValueError):
            pass

        r = app.test_client().post(
            "/api/scan/start",
            json={"domain": domain, "modules": modules, "threads": threads},
            content_type="application/json",
        )
        data = r.get_json()
        if "error" in data:
            return respond([f"ERROR: {data['error']}"])
        sid = data["scan_id"]
        return respond([
            f"✓ Scan started for [{domain}]",
            f"  Modules : {', '.join(modules)}",
            f"  Threads : {threads}",
            f"  Scan ID : {sid}",
            f"  Use  →  status {sid}  to follow progress",
        ])

    if verb == "status":
        if len(parts) < 2:
            return respond(["Usage: status <scan_id>"])
        sid = parts[1]
        with SCANS_LOCK:
            scan = SCANS.get(sid)
        if not scan:
            return respond([f"No scan found with ID: {sid}"])
        lines = [f"Scan [{sid}]  status: {scan['status'].upper()}"]
        lines += scan["logs"][-20:]
        if scan["status"] == "done":
            r = scan["result"]
            lines.append(f"  Subdomains : {len(r.get('subdomains', []))}")
            lines.append(f"  Dirs found : {len(r.get('directories', []))}")
            lines.append(f"  Vuln hints : {len(r.get('vulnerabilities', []))}")
        return respond(lines)

    if verb == "show":
        if len(parts) < 2:
            return respond(["Usage: show subdomains <domain> | show results"])
        sub_verb = parts[1].lower()

        if sub_verb == "results":
            if not DB_AVAILABLE:
                return respond(["Database unavailable."])
            user = current_user()
            rows = get_all_results() if is_admin() else get_all_results(username=user["username"])
            if not rows:
                return respond(["No scan results in database yet."])
            lines = ["Domain                    | Subs | Dirs | Vulns | Scanned By      | Added At"]
            lines.append("─" * 80)
            for row in rows:
                lines.append(
                    f"{str(row['domain']):<26}| "
                    f"{str(row['subdomain_count'] or 0):<5}| "
                    f"{str(row['directory_count'] or 0):<5}| "
                    f"{str(row['vuln_count'] or 0):<6}| "
                    f"{str(row.get('scanned_by','?')):<16}| "
                    f"{str(row['added_at'])[:19]}"
                )
            return respond(lines)

        if sub_verb == "subdomains":
            if len(parts) < 3:
                return respond(["Usage: show subdomains <domain>"])
            domain = parts[2]
            if not DB_AVAILABLE:
                return respond(["Database unavailable."])
            detail = get_target_detail(domain)
            if not detail:
                return respond([f"No data found for domain: {domain}"])
            lines = [f"Subdomains for {domain}:"]
            for s in detail.get("subdomains", []):
                lines.append(f"  · {s['subdomain']}")
            return respond(lines if len(lines) > 1 else [f"No subdomains saved for {domain}"])

    return respond([f"Unknown command: '{verb}'. Type 'help' for available commands."])


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
