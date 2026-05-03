import os
from flask import Flask
from flask_mail import Mail
from app.models import db, login_manager

mail = Mail()


def create_app():
    app = Flask(__name__)

    # ── Config ──────────────────────────────────────────────────────────────
    from config import Config
    app.config.from_object(Config)

    # Ensure upload directory exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # ── Extensions ──────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # ── DB tables (safe: only runs if connection succeeds) ───────────────────
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"db.create_all() skipped: {e}")

    # ── Blueprints ──────────────────────────────────────────────────────────
    from app.auth.routes import auth_bp
    from app.events.routes import events_bp
    from app.registrations.routes import registrations_bp
    from app.payments.routes import payments_bp
    from app.analytics.routes import analytics_bp

    app.register_blueprint(auth_bp,          url_prefix='/auth')
    app.register_blueprint(events_bp,        url_prefix='/events')
    app.register_blueprint(registrations_bp, url_prefix='/registrations')
    app.register_blueprint(payments_bp,      url_prefix='')
    app.register_blueprint(analytics_bp,     url_prefix='/analytics')

    # ── Core routes (defined at module level via a helper to stay picklable) ─
    _register_core_routes(app)

    return app


def _register_core_routes(app):
    """Register root-level routes outside create_app closure for gunicorn fork safety."""
    from flask import redirect, url_for

    @app.route('/')
    def index():
        return redirect(url_for('events.home'))

    @app.route('/health')
    def health():
        return 'EventSpheres Running 🚀', 200

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        now = datetime.utcnow()
        return {'now': now, 'current_year': now.year}