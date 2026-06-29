"""
backend/routes/dashboard.py
============================
Serves the frontend HTML dashboard.
"""

from flask import Blueprint, render_template
from backend.utils.message_store import get_stats

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    stats = get_stats()
    return render_template("dashboard.html", stats=stats)
