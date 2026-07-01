"""
backend/routes/dashboard.py
============================
Serves the public landing page and the staff dashboard.

Audience separation (by URL):
    /            -> landing page (front door for everyone)
    /chat        -> guest chat        (clients)        [served in routes/chat.py]
    /dashboard   -> staff dashboard   (TDU team)
"""

from flask import Blueprint, render_template
from backend.utils.message_store import get_stats

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def landing():
    """Public front door — routes guests to the chat and staff to the dashboard."""
    return render_template("landing.html")


@dashboard_bp.route("/dashboard")
def dashboard():
    """Staff-facing live dashboard."""
    stats = get_stats()
    return render_template("dashboard.html", stats=stats)    
