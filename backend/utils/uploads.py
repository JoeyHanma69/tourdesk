"""
backend/utils/uploads.py
==========================
Handles file/image attachments sent from the guest chatbot composer or a
staff reply on the dashboard. Files are saved under frontend/static/uploads
and served back as regular static assets.
"""

import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp",
    "pdf", "doc", "docx", "txt",
}

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "frontend" / "static" / "uploads"


class InvalidUpload(Exception):
    pass


def save_upload(file_storage) -> dict:
    """Validate and save an uploaded file. Returns {url, filename, mime}."""
    filename = file_storage.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidUpload(f"Unsupported file type: .{ext}" if ext else "File has no extension")

    safe_name = secure_filename(filename)
    if not safe_name:
        raise InvalidUpload("Invalid filename")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Prefix with a uuid so concurrent guests can't collide or overwrite
    # each other's files, and so a client can't guess another upload's URL.
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest = UPLOAD_DIR / stored_name
    file_storage.save(dest)

    is_image = ext in {"png", "jpg", "jpeg", "gif", "webp"}

    return {
        "url":      f"/static/uploads/{stored_name}",
        "filename": safe_name,
        "mime":     file_storage.mimetype,
        "is_image": is_image,
    }
