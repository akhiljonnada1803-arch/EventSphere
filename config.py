import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _get_db_url():
    """Return a SQLAlchemy-compatible DB URL, fixing Render's postgres:// prefix."""
    url = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'events.db')
    )
    # Render provides postgres:// but SQLAlchemy 1.4+ needs postgresql://
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


class Config:
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = _get_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,       # avoids stale-connection crashes
        'pool_recycle': 300,         # recycle connections every 5 min
    }

    # ── Mail ──────────────────────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.sendgrid.net')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'apikey')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_PASSWORD', '') == ''  # suppress if unconfigured

    # ── Razorpay ──────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_Sk3dYRoIgZ5ZWD')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'NDzV8HmdjY7uQg8iWZbYRvIx')

    # ── Uploads ───────────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
