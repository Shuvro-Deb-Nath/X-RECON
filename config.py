# ─────────────────────────────────────────────────────────────
#  RECON-X  ·  Configuration
# ─────────────────────────────────────────────────────────────

# Flask
SECRET_KEY = "recon-x-super-secret-key-2024"
DEBUG = True
PORT = 5000

# MySQL – update these to match your local installation
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "root"          # ← change me
DB_NAME     = "reconx_db"

# Module B defaults
DEFAULT_THREADS     = 20
REQUEST_TIMEOUT     = 5        # seconds
INTERESTING_CODES   = [200, 201, 301, 302, 403, 405, 500]
