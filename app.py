"""
FA Events — Event & Wedding Decoration Website
Flask backend: public site, enquiry form, star ratings, and an
admin dashboard for managing photos, videos, enquiries and reviews.

Run locally:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000

Default admin login (CHANGE THIS before going live — see README.md):
    username: admin
    password: faevents2026
"""

import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory, g
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "faevents.db")
PHOTO_DIR = os.path.join(BASE_DIR, "static", "uploads", "photos")
VIDEO_DIR = os.path.join(BASE_DIR, "static", "uploads", "videos")

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov"}
MAX_CONTENT_LENGTH = 60 * 1024 * 1024  # 60 MB per upload

app = Flask(__name__)
app.secret_key = os.environ.get("FA_SECRET_KEY", "change-this-secret-key-in-production")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# ---------------------------------------------------------------------------
# Business info — edit these to update the site's contact details & SEO
# ---------------------------------------------------------------------------
BUSINESS = {
    "name": "FA Events",
    "tagline": "Event & Wedding Decoration across Kanyakumari District",
    "phone_display": "+91 90000 00000",
    "phone_tel": "+919000000000",
    "whatsapp_number": "919000000000",          # digits only, country code first
    "whatsapp_group_link": "https://chat.whatsapp.com/your-group-invite-link",
    "instagram_handle": "@faevents",
    "instagram_link": "https://instagram.com/faevents",
    "email": "faevents.enquiry@gmail.com",
    "address_line": "Parvathipuram, Nagercoil, Kanyakumari District, Tamil Nadu",
    "areas_served": "Parvathipuram, Nagercoil, Kanyakumari, Colachel, Marthandam, Thuckalay, KK District",
    "map_embed_src": "https://www.google.com/maps?q=Nagercoil,Kanyakumari&output=embed",
    "google_business_profile": "",  # paste your Google Business Profile share link
}

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    first_run = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            event_type TEXT,
            event_date TEXT,
            location TEXT,
            message TEXT,
            created_at TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            caption TEXT,
            category TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            embed_url TEXT,
            caption TEXT,
            category TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stars INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    db.commit()

    if first_run:
        # Seed a default admin account on first run only.
        db.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            ("admin", generate_password_hash("faevents2026")),
        )
        db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def notify_owner_new_enquiry(enquiry):
    """
    Best-effort email notification to the owner when a new enquiry arrives.
    Configure FA_SMTP_* environment variables to enable this — if they are
    not set, this silently does nothing and the enquiry still appears in
    the admin dashboard, so nothing is ever lost.
    """
    smtp_host = os.environ.get("FA_SMTP_HOST")
    smtp_user = os.environ.get("FA_SMTP_USER")
    smtp_pass = os.environ.get("FA_SMTP_PASS")
    owner_email = os.environ.get("FA_OWNER_EMAIL", BUSINESS["email"])

    if not (smtp_host and smtp_user and smtp_pass and owner_email):
        return  # Not configured — dashboard badge is still the source of truth.

    body = (
        f"New enquiry received on the FA Events website:\n\n"
        f"Name: {enquiry['name']}\n"
        f"Phone: {enquiry['phone']}\n"
        f"Email: {enquiry.get('email') or '-'}\n"
        f"Event type: {enquiry.get('event_type') or '-'}\n"
        f"Event date: {enquiry.get('event_date') or '-'}\n"
        f"Location: {enquiry.get('location') or '-'}\n"
        f"Message: {enquiry.get('message') or '-'}\n"
    )
    msg = MIMEText(body)
    msg["Subject"] = f"New enquiry from {enquiry['name']} — FA Events website"
    msg["From"] = smtp_user
    msg["To"] = owner_email

    try:
        smtp_port = int(os.environ.get("FA_SMTP_PORT", "587"))
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as exc:  # pragma: no cover - best effort only
        app.logger.warning("Enquiry email notification failed: %s", exc)


# ---------------------------------------------------------------------------
# Public site routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    db = get_db()
    photos = db.execute(
        "SELECT * FROM photos ORDER BY created_at DESC LIMIT 12"
    ).fetchall()
    videos = db.execute(
        "SELECT * FROM videos ORDER BY created_at DESC LIMIT 8"
    ).fetchall()
    ratings = db.execute(
        "SELECT * FROM ratings WHERE approved = 1 ORDER BY created_at DESC LIMIT 12"
    ).fetchall()
    avg_row = db.execute(
        "SELECT AVG(stars) AS avg_stars, COUNT(*) AS total FROM ratings WHERE approved = 1"
    ).fetchone()
    avg_stars = round(avg_row["avg_stars"], 1) if avg_row["avg_stars"] else 0
    total_ratings = avg_row["total"] or 0

    return render_template(
        "index.html",
        biz=BUSINESS,
        photos=photos,
        videos=videos,
        ratings=ratings,
        avg_stars=avg_stars,
        total_ratings=total_ratings,
    )


@app.route("/enquiry", methods=["POST"])
def submit_enquiry():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    event_type = request.form.get("event_type", "").strip()
    event_date = request.form.get("event_date", "").strip()
    location = request.form.get("location", "").strip()
    message = request.form.get("message", "").strip()
    # Honeypot spam trap — real visitors never fill this hidden field.
    honeypot = request.form.get("website", "")

    if honeypot:
        return jsonify({"ok": True})  # silently drop bots, pretend success

    if not name or not phone:
        return jsonify({"ok": False, "error": "Please share your name and phone number."}), 400

    db = get_db()
    now = datetime.now().isoformat(timespec="seconds")
    db.execute(
        """INSERT INTO enquiries
           (name, phone, email, event_type, event_date, location, message, created_at, is_read)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (name, phone, email, event_type, event_date, location, message, now),
    )
    db.commit()

    notify_owner_new_enquiry({
        "name": name, "phone": phone, "email": email, "event_type": event_type,
        "event_date": event_date, "location": location, "message": message,
    })

    return jsonify({"ok": True})


@app.route("/rating", methods=["POST"])
def submit_rating():
    name = request.form.get("name", "").strip()
    stars = request.form.get("stars", "").strip()
    comment = request.form.get("comment", "").strip()
    honeypot = request.form.get("website", "")

    if honeypot:
        return jsonify({"ok": True})

    if not name or stars not in {"1", "2", "3", "4", "5"}:
        return jsonify({"ok": False, "error": "Please add your name and a star rating."}), 400

    db = get_db()
    now = datetime.now().isoformat(timespec="seconds")
    db.execute(
        "INSERT INTO ratings (name, stars, comment, created_at, approved) VALUES (?, ?, ?, ?, 0)",
        (name, int(stars), comment, now),
    )
    db.commit()
    return jsonify({"ok": True, "message": "Thanks! Your review will appear after a quick check."})


@app.route("/robots.txt")
def robots_txt():
    return (
        "User-agent: *\nAllow: /\nSitemap: " + request.url_root + "sitemap.xml\n",
        200,
        {"Content-Type": "text/plain"},
    )


@app.route("/sitemap.xml")
def sitemap_xml():
    root = request.url_root.rstrip("/")
    urls = [root + "/"]
    body = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'
    return xml, 200, {"Content-Type": "application/xml"}


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        row = db.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            session.clear()
            session["admin_id"] = row["id"]
            session["admin_username"] = row["username"]
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("Incorrect username or password.")
    return render_template("admin_login.html", biz=BUSINESS)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    unread_count = db.execute(
        "SELECT COUNT(*) c FROM enquiries WHERE is_read = 0"
    ).fetchone()["c"]
    enquiries = db.execute(
        "SELECT * FROM enquiries ORDER BY created_at DESC"
    ).fetchall()
    photos = db.execute("SELECT * FROM photos ORDER BY created_at DESC").fetchall()
    videos = db.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
    ratings = db.execute("SELECT * FROM ratings ORDER BY created_at DESC").fetchall()
    pending_ratings = sum(1 for r in ratings if not r["approved"])

    return render_template(
        "admin_dashboard.html",
        biz=BUSINESS,
        enquiries=enquiries,
        unread_count=unread_count,
        photos=photos,
        videos=videos,
        ratings=ratings,
        pending_ratings=pending_ratings,
    )


@app.route("/admin/enquiry/<int:enquiry_id>/read", methods=["POST"])
@login_required
def mark_enquiry_read(enquiry_id):
    db = get_db()
    db.execute("UPDATE enquiries SET is_read = 1 WHERE id = ?", (enquiry_id,))
    db.commit()
    return redirect(url_for("admin_dashboard") + "#enquiries")


@app.route("/admin/enquiry/<int:enquiry_id>/delete", methods=["POST"])
@login_required
def delete_enquiry(enquiry_id):
    db = get_db()
    db.execute("DELETE FROM enquiries WHERE id = ?", (enquiry_id,))
    db.commit()
    return redirect(url_for("admin_dashboard") + "#enquiries")


@app.route("/admin/photo/upload", methods=["POST"])
@login_required
def upload_photo():
    file = request.files.get("photo")
    caption = request.form.get("caption", "").strip()
    category = request.form.get("category", "").strip()

    if not file or file.filename == "":
        flash("Please choose a photo to upload.")
        return redirect(url_for("admin_dashboard") + "#gallery")

    if not allowed_file(file.filename, ALLOWED_IMAGE_EXT):
        flash("Unsupported image format. Use JPG, PNG, WEBP or GIF.")
        return redirect(url_for("admin_dashboard") + "#gallery")

    filename = secure_filename(file.filename)
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    file.save(os.path.join(PHOTO_DIR, unique_name))

    db = get_db()
    db.execute(
        "INSERT INTO photos (filename, caption, category, created_at) VALUES (?, ?, ?, ?)",
        (unique_name, caption, category, datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("Photo uploaded.")
    return redirect(url_for("admin_dashboard") + "#gallery")


@app.route("/admin/photo/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    db = get_db()
    row = db.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if row:
        path = os.path.join(PHOTO_DIR, row["filename"])
        if os.path.exists(path):
            os.remove(path)
        db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        db.commit()
    return redirect(url_for("admin_dashboard") + "#gallery")


@app.route("/admin/video/upload", methods=["POST"])
@login_required
def upload_video():
    file = request.files.get("video")
    embed_url = request.form.get("embed_url", "").strip()
    caption = request.form.get("caption", "").strip()
    category = request.form.get("category", "").strip()
    now = datetime.now().isoformat(timespec="seconds")

    filename = None
    if file and file.filename:
        if not allowed_file(file.filename, ALLOWED_VIDEO_EXT):
            flash("Unsupported video format. Use MP4, WEBM or MOV.")
            return redirect(url_for("admin_dashboard") + "#videos")
        safe = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe}"
        file.save(os.path.join(VIDEO_DIR, filename))

    if not filename and not embed_url:
        flash("Upload a video file or paste a YouTube/Instagram embed link.")
        return redirect(url_for("admin_dashboard") + "#videos")

    db = get_db()
    db.execute(
        "INSERT INTO videos (filename, embed_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?)",
        (filename, embed_url, caption, category, now),
    )
    db.commit()
    flash("Video added.")
    return redirect(url_for("admin_dashboard") + "#videos")


@app.route("/admin/video/<int:video_id>/delete", methods=["POST"])
@login_required
def delete_video(video_id):
    db = get_db()
    row = db.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
    if row:
        if row["filename"]:
            path = os.path.join(VIDEO_DIR, row["filename"])
            if os.path.exists(path):
                os.remove(path)
        db.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        db.commit()
    return redirect(url_for("admin_dashboard") + "#videos")


@app.route("/admin/rating/<int:rating_id>/approve", methods=["POST"])
@login_required
def approve_rating(rating_id):
    db = get_db()
    db.execute("UPDATE ratings SET approved = 1 WHERE id = ?", (rating_id,))
    db.commit()
    return redirect(url_for("admin_dashboard") + "#reviews")


@app.route("/admin/rating/<int:rating_id>/delete", methods=["POST"])
@login_required
def delete_rating(rating_id):
    db = get_db()
    db.execute("DELETE FROM ratings WHERE id = ?", (rating_id,))
    db.commit()
    return redirect(url_for("admin_dashboard") + "#reviews")


@app.route("/admin/change-password", methods=["POST"])
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    db = get_db()
    row = db.execute("SELECT * FROM admin WHERE id = ?", (session["admin_id"],)).fetchone()

    if not row or not check_password_hash(row["password_hash"], current):
        flash("Current password is incorrect.")
    elif len(new) < 8:
        flash("New password must be at least 8 characters.")
    elif new != confirm:
        flash("New password and confirmation do not match.")
    else:
        db.execute(
            "UPDATE admin SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new), row["id"]),
        )
        db.commit()
        flash("Password updated.")
    return redirect(url_for("admin_dashboard") + "#settings")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
else:
    init_db()
