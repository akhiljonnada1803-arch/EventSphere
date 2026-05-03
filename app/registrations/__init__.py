from flask import Blueprint

registrations_bp = Blueprint('registrations', __name__)

from app.registrations import routes  # noqa: F401, E402
