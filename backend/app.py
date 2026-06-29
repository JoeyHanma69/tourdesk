"""
app.py — TourDesk AI Flask Application
=======================================
Entry point. Registers all route blueprints and starts the server.

Run locally:
    python backend/app.py

With gunicorn (production):
    gunicorn -w 2 -b 0.0.0.0:5000 backend.app:app
"""

import os
from flask import Flask
from flask_cors import CORS

from backend.routes.chat import chat_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.api import api_bp
from backend.utils.classifier import TourDeskClassifier

# ── App factory ──────────────────────────────────────────────────────────────
def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    CORS(app)

    # Load config from environment (or .env file via python-dotenv)
    app.config["SECRET_KEY"]           = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["MODEL_DIR"]            = os.getenv("MODEL_DIR", "ml_classifier/model")
    app.config["CONFIDENCE_THRESHOLD"] = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))

    # Boot the classifier once at startup (not per-request)
    app.classifier = TourDeskClassifier(
        model_dir=app.config["MODEL_DIR"],
        threshold=app.config["CONFIDENCE_THRESHOLD"],
    )

    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 TourDesk AI running on http://localhost:{port}")
    app.run(debug=True, host="0.0.0.0", port=port)
