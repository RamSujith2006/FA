"""
FA Events — Event & Wedding Decoration Website
With Integrated Firebase Cloud Storage for Photos & Videos

Default admin login:
    username: admin
    password: faevents2026
"""

import os
import sqlite3
import smtplib
import json
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

# Automatically load environment variables from .env file if present
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Cloudinary Storage Integration (Alternative / Large Media Storage)
# ---------------------------------------------------------------------------
HAS_CLOUDINARY = False
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True
        )
        HAS_CLOUDINARY = True
        print(f"[Cloudinary Storage] Connected! Cloud Name: {CLOUDINARY_CLOUD_NAME}")
    except Exception as exc:
        print(f"[Cloudinary Storage] Notice: {exc}")

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov"}
MAX_CONTENT_LENGTH = 60 * 1024 * 1024  # 60 MB per upload

os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FA_SECRET_KEY", "change-this-secret-key-in-production")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# ---------------------------------------------------------------------------
# Business info — edit these to update the site's contact details & SEO
# ---------------------------------------------------------------------------
BUSINESS = {
    "name": "FA Events",
    "tagline": "Event & Wedding Decoration across Kanyakumari District",
    "phone_display": "+91 78453 28583",
    "phone_tel": "+917845328583",
    "whatsapp_number": "917845328583",          # digits only, country code first
    "whatsapp_group_link": "https://chat.whatsapp.com/I7Bxb77gi6X008AgRo1zD2",
    "instagram_handle": "@f.a_event",
    "instagram_link": "https://www.instagram.com/f.a_event?utm_source=qr&stkn=MTZtamxkcnpjYXQ3aA==",
    "email": "faevents123@gmail.com",
    "address_line": "F.A events, Christopher Colony, Nagercoil, Tamil Nadu 629003",
    "areas_served": "Christopher Colony, Parvathipuram, Nagercoil, Kanyakumari, Colachel, Marthandam, Thuckalay, KK District",
    "map_embed_src": "https://www.google.com/maps?q=F.A+events,+Christopher+Colony,+Nagercoil,+Tamil+Nadu+629003&output=embed",
    "google_business_profile": "https://maps.app.goo.gl/paL8VoVXGBfmLZhH9",
}

# ---------------------------------------------------------------------------
# Firebase Cloud Database & Storage Integration
# ---------------------------------------------------------------------------
FIREBASE_DB = None
FIREBASE_BUCKET = None
FIREBASE_BUCKET_NAME = None

def init_firebase():
    global FIREBASE_DB, FIREBASE_BUCKET, FIREBASE_BUCKET_NAME
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    if not cred_path:
        for p in [os.path.join(BASE_DIR, "firebase_key.json.json"), os.path.join(BASE_DIR, "firebase_key.json")]:
            if os.path.exists(p):
                cred_path = p
                break

    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")

    if cred_path and os.path.exists(cred_path):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore, storage

            if not bucket_name:
                try:
                    with open(cred_path, "r", encoding="utf-8") as f:
                        cred_data = json.load(f)
                        project_id = cred_data.get("project_id")
                        if project_id:
                            bucket_name = f"{project_id}.appspot.com"
                except Exception:
                    pass

            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                options = {"storageBucket": bucket_name} if bucket_name else {}
                firebase_admin.initialize_app(cred, options)

            FIREBASE_DB = firestore.client()
            if bucket_name:
                FIREBASE_BUCKET = storage.bucket(bucket_name)
                FIREBASE_BUCKET_NAME = bucket_name
            else:
                FIREBASE_BUCKET = storage.bucket()
                FIREBASE_BUCKET_NAME = FIREBASE_BUCKET.name if FIREBASE_BUCKET else "Default Bucket"
            print(f"[Firebase Storage] Connected to Cloud Storage! Bucket: {FIREBASE_BUCKET_NAME}")
        except Exception as exc:
            print(f"[Firebase Storage] Notice: {exc}")


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
            created_at TEXT NOT NULL,
            cloud_url TEXT
        );

        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            embed_url TEXT,
            caption TEXT,
            category TEXT,
            created_at TEXT NOT NULL,
            cloud_url TEXT
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

    # Column migration for cloud storage URLs
    for table in ["photos", "videos"]:
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN cloud_url TEXT")
        except sqlite3.OperationalError:
            pass
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
    smtp_host = os.environ.get("FA_SMTP_HOST")
    smtp_user = os.environ.get("FA_SMTP_USER")
    smtp_pass = os.environ.get("FA_SMTP_PASS")
    owner_email = os.environ.get("FA_OWNER_EMAIL", BUSINESS["email"])

    if not (smtp_host and smtp_user and smtp_pass and owner_email):
        return

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
    except Exception as exc:
        app.logger.warning("Enquiry email notification failed: %s", exc)


# ---------------------------------------------------------------------------
# Public site routes & SEO endpoints
# ---------------------------------------------------------------------------

@app.route("/sitemap.xml")
def sitemap():
    host = request.url_root.rstrip("/")
    now = datetime.now().strftime("%Y-%m-%d")
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{host}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return app.response_class(xml_content, mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    host = request.url_root.rstrip("/")
    content = f"User-agent: *\nAllow: /\nSitemap: {host}/sitemap.xml\n"
    return app.response_class(content, mimetype="text/plain")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def index():
    db = get_db()
    photos = db.execute("SELECT * FROM photos ORDER BY created_at DESC").fetchall()
    videos = db.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()

    photo_categories = sorted(list({p["category"] for p in photos if p["category"]}))
    video_categories = sorted(list({v["category"] for v in videos if v["category"]}))

    approved_ratings = db.execute(
        "SELECT * FROM ratings WHERE approved = 1 ORDER BY created_at DESC"
    ).fetchall()

    if approved_ratings:
        avg_stars = round(sum(r["stars"] for r in approved_ratings) / len(approved_ratings), 1)
        total_reviews = len(approved_ratings)
    else:
        avg_stars = 5.0
        total_reviews = 0

    return render_template(
        "index.html",
        biz=BUSINESS,
        photos=photos,
        videos=videos,
        photo_categories=photo_categories,
        video_categories=video_categories,
        ratings=approved_ratings,
        avg_stars=avg_stars,
        total_reviews=total_reviews,
    )


@app.route("/enquire", methods=["POST"])
def submit_enquiry():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    event_type = request.form.get("event_type", "").strip()
    event_date = request.form.get("event_date", "").strip()
    location = request.form.get("location", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not phone:
        flash("Please provide your name and phone number.")
        return redirect(url_for("index") + "#contact")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO enquiries (name, phone, email, event_type, event_date, location, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, phone, email, event_type, event_date, location, message, now),
    )
    db.commit()
    enquiry_id = cursor.lastrowid

    if FIREBASE_DB:
        try:
            FIREBASE_DB.collection("enquiries").document(str(enquiry_id)).set({
                "id": enquiry_id,
                "name": name,
                "phone": phone,
                "email": email,
                "event_type": event_type,
                "event_date": event_date,
                "location": location,
                "message": message,
                "created_at": now,
                "is_read": False,
            })
        except Exception as exc:
            app.logger.warning("Firestore enquiry save failed: %s", exc)

    notify_owner_new_enquiry({
        "name": name, "phone": phone, "email": email,
        "event_type": event_type, "event_date": event_date,
        "location": location, "message": message,
    })

    flash("Thank you! Your enquiry has been sent. We will call you back shortly.")
    return redirect(url_for("index") + "#contact")


@app.route("/rating/submit", methods=["POST"])
def submit_rating():
    name = request.form.get("name", "").strip()
    stars = request.form.get("stars", "5")
    comment = request.form.get("comment", "").strip()

    try:
        stars_int = int(stars)
        if stars_int < 1 or stars_int > 5:
            stars_int = 5
    except ValueError:
        stars_int = 5

    if not name:
        flash("Please enter your name for the review.")
        return redirect(url_for("index") + "#reviews")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute(
        "INSERT INTO ratings (name, stars, comment, created_at, approved) VALUES (?, ?, ?, ?, 0)",
        (name, stars_int, comment, now),
    )
    db.commit()

    flash("Thank you for your rating! It will appear on the website once approved by our team.")
    return redirect(url_for("index") + "#reviews")


# ---------------------------------------------------------------------------
# Admin authentication
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM admin WHERE username = ?", (username,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["admin_id"] = user["id"]
            session["admin_user"] = user["username"]
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin_dashboard"))
        else:
            flash("Invalid username or password.")

    return render_template("admin_login.html", biz=BUSINESS)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("admin_login"))


# ---------------------------------------------------------------------------
# Admin Dashboard & Cloud Storage REST API
# ---------------------------------------------------------------------------

def format_bytes(size):
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def upload_file_to_firebase(local_path, folder, filename):
    cloud_url = None

    # Priority 1: Cloudinary Storage for Photos & Videos
    if HAS_CLOUDINARY:
        try:
            import cloudinary.uploader
            res_type = "video" if folder == "videos" else "image"
            res = cloudinary.uploader.upload(
                local_path,
                folder=f"fa-events/{folder}",
                public_id=filename.rsplit(".", 1)[0],
                resource_type=res_type
            )
            cloud_url = res.get("secure_url") or res.get("url")
            print(f"[Cloudinary Storage Upload]: {filename} -> {cloud_url}")
            return cloud_url
        except Exception as exc:
            app.logger.warning("Cloudinary media upload failed: %s", exc)

    # Priority 2: Firebase Storage Fallback
    if FIREBASE_BUCKET:
        try:
            blob_name = f"{folder}/{filename}"
            blob = FIREBASE_BUCKET.blob(blob_name)
            blob.upload_from_filename(local_path)
            try:
                blob.make_public()
                cloud_url = blob.public_url
            except Exception:
                cloud_url = f"https://storage.googleapis.com/{FIREBASE_BUCKET.name}/{blob_name}"
            print(f"[Firebase Storage Upload]: {blob_name} -> {cloud_url}")
            return cloud_url
        except Exception as exc:
            app.logger.warning("Firebase Storage upload failed: %s", exc)

    return cloud_url


def delete_file_from_firebase(folder, filename):
    if FIREBASE_BUCKET and filename:
        try:
            blob_name = f"{folder}/{filename}"
            blob = FIREBASE_BUCKET.blob(blob_name)
            if blob.exists():
                blob.delete()
                print(f"[Firebase Storage Delete]: {blob_name}")
        except Exception as exc:
            app.logger.warning("Firebase Storage delete failed: %s", exc)


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

    total_bytes = 0
    for p in photos:
        loc = os.path.join(PHOTO_DIR, p["filename"])
        if os.path.exists(loc):
            total_bytes += os.path.getsize(loc)
    for v in videos:
        if v["filename"]:
            loc = os.path.join(VIDEO_DIR, v["filename"])
            if os.path.exists(loc):
                total_bytes += os.path.getsize(loc)

    firebase_status = {
        "connected": FIREBASE_BUCKET is not None,
        "bucket_name": FIREBASE_BUCKET_NAME or "Local Emulated Storage",
        "provider": "Firebase Cloud Storage" if FIREBASE_BUCKET else "Local Cloud Emulator",
        "total_files": len(photos) + sum(1 for v in videos if v["filename"]),
        "total_bytes": total_bytes,
        "total_bytes_formatted": format_bytes(total_bytes)
    }

    return render_template(
        "admin_dashboard.html",
        biz=BUSINESS,
        enquiries=enquiries,
        unread_count=unread_count,
        photos=photos,
        videos=videos,
        ratings=ratings,
        pending_ratings=pending_ratings,
        firebase_status=firebase_status
    )


@app.route("/admin/api/cloud-storage/status")
@login_required
def api_cloud_storage_status():
    db = get_db()
    photos = db.execute("SELECT * FROM photos").fetchall()
    videos = db.execute("SELECT * FROM videos").fetchall()

    total_bytes = 0
    photo_count = len(photos)
    video_count = 0

    for p in photos:
        loc = os.path.join(PHOTO_DIR, p["filename"])
        if os.path.exists(loc):
            total_bytes += os.path.getsize(loc)

    for v in videos:
        if v["filename"]:
            video_count += 1
            loc = os.path.join(VIDEO_DIR, v["filename"])
            if os.path.exists(loc):
                total_bytes += os.path.getsize(loc)

    return jsonify({
        "connected": FIREBASE_BUCKET is not None,
        "provider": "Firebase Cloud Storage" if FIREBASE_BUCKET else "Local Cloud Emulator",
        "bucket_name": FIREBASE_BUCKET_NAME or "local-storage-emulator",
        "photo_count": photo_count,
        "video_count": video_count,
        "total_files": photo_count + video_count,
        "total_bytes": total_bytes,
        "total_bytes_formatted": format_bytes(total_bytes)
    })


@app.route("/admin/api/cloud-storage/files")
@login_required
def api_cloud_storage_files():
    folder = request.args.get("folder", "all").strip().lower()
    search = request.args.get("q", "").strip().lower()

    db = get_db()
    file_list = []

    if folder in ["all", "photos"]:
        photos = db.execute("SELECT * FROM photos ORDER BY created_at DESC").fetchall()
        for p in photos:
            loc = os.path.join(PHOTO_DIR, p["filename"])
            size = os.path.getsize(loc) if os.path.exists(loc) else 0
            caption = p["caption"] or ""
            category = p["category"] or ""
            if search and (search not in p["filename"].lower() and search not in caption.lower() and search not in category.lower()):
                continue

            ext = p["filename"].rsplit(".", 1)[-1].lower() if "." in p["filename"] else "jpg"
            mime_type = f"image/{ext}" if ext != "svg" else "image/svg+xml"
            local_url = url_for("static", filename=f"uploads/photos/{p['filename']}")
            cloud_url = p["cloud_url"] if "cloud_url" in p.keys() and p["cloud_url"] else None

            file_list.append({
                "id": p["id"],
                "type": "photo",
                "filename": p["filename"],
                "folder": "photos",
                "caption": caption,
                "category": category,
                "created_at": p["created_at"],
                "size_bytes": size,
                "size_formatted": format_bytes(size),
                "mime_type": mime_type,
                "local_url": local_url,
                "cloud_url": cloud_url,
                "display_url": cloud_url or local_url,
                "is_cloud_synced": bool(cloud_url or FIREBASE_BUCKET)
            })

    if folder in ["all", "videos"]:
        videos = db.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        for v in videos:
            filename = v["filename"]
            caption = v["caption"] or ""
            category = v["category"] or ""
            embed_url = v["embed_url"] or ""

            if search and (search not in (filename or "").lower() and search not in caption.lower() and search not in category.lower()):
                continue

            if filename:
                loc = os.path.join(VIDEO_DIR, filename)
                size = os.path.getsize(loc) if os.path.exists(loc) else 0
                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp4"
                mime_type = f"video/{ext}"
                local_url = url_for("static", filename=f"uploads/videos/{filename}")
                cloud_url = v["cloud_url"] if "cloud_url" in v.keys() and v["cloud_url"] else None

                file_list.append({
                    "id": v["id"],
                    "type": "video",
                    "filename": filename,
                    "folder": "videos",
                    "caption": caption,
                    "category": category,
                    "created_at": v["created_at"],
                    "size_bytes": size,
                    "size_formatted": format_bytes(size),
                    "mime_type": mime_type,
                    "local_url": local_url,
                    "cloud_url": cloud_url,
                    "display_url": cloud_url or local_url,
                    "embed_url": embed_url,
                    "is_cloud_synced": bool(cloud_url or FIREBASE_BUCKET)
                })
            elif embed_url:
                file_list.append({
                    "id": v["id"],
                    "type": "video_embed",
                    "filename": "Embed Link",
                    "folder": "videos",
                    "caption": caption,
                    "category": category,
                    "created_at": v["created_at"],
                    "size_bytes": 0,
                    "size_formatted": "External",
                    "mime_type": "video/embed",
                    "embed_url": embed_url,
                    "display_url": embed_url,
                    "is_cloud_synced": True
                })

    return jsonify({"files": file_list, "count": len(file_list)})


@app.route("/admin/api/cloud-storage/upload", methods=["POST"])
@login_required
def api_cloud_storage_upload():
    uploaded_files = request.files.getlist("files") or ([request.files.get("file")] if request.files.get("file") else [])
    caption = request.form.get("caption", "").strip()
    category = request.form.get("category", "").strip()
    folder_override = request.form.get("folder", "").strip().lower()

    if not uploaded_files or not uploaded_files[0] or uploaded_files[0].filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    results = []
    db = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for file in uploaded_files:
        if not file or not file.filename:
            continue

        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        is_img = ext in ALLOWED_IMAGE_EXT
        is_vid = ext in ALLOWED_VIDEO_EXT

        if folder_override == "photos":
            is_img = True
        elif folder_override == "videos":
            is_vid = True

        if not is_img and not is_vid:
            continue

        unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"

        if is_img:
            local_path = os.path.join(PHOTO_DIR, unique_name)
            file.save(local_path)
            cloud_url = upload_file_to_firebase(local_path, "photos", unique_name)

            db.execute(
                "INSERT INTO photos (filename, cloud_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?)",
                (unique_name, cloud_url, caption, category, now),
            )
            db.commit()

            if FIREBASE_DB:
                try:
                    FIREBASE_DB.collection("photos").document(unique_name).set({
                        "filename": unique_name,
                        "cloud_url": cloud_url,
                        "caption": caption,
                        "category": category,
                        "created_at": now,
                    })
                except Exception as exc:
                    app.logger.warning("Firestore photo sync warning: %s", exc)

            results.append({
                "type": "photo",
                "filename": unique_name,
                "folder": "photos",
                "cloud_url": cloud_url,
                "local_url": url_for("static", filename=f"uploads/photos/{unique_name}")
            })

        elif is_vid:
            local_path = os.path.join(VIDEO_DIR, unique_name)
            file.save(local_path)
            cloud_url = upload_file_to_firebase(local_path, "videos", unique_name)

            db.execute(
                "INSERT INTO videos (filename, cloud_url, embed_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (unique_name, cloud_url, "", caption, category, now),
            )
            db.commit()

            if FIREBASE_DB:
                try:
                    FIREBASE_DB.collection("videos").document(unique_name).set({
                        "filename": unique_name,
                        "cloud_url": cloud_url,
                        "embed_url": "",
                        "caption": caption,
                        "category": category,
                        "created_at": now,
                    })
                except Exception as exc:
                    app.logger.warning("Firestore video sync warning: %s", exc)

            results.append({
                "type": "video",
                "filename": unique_name,
                "folder": "videos",
                "cloud_url": cloud_url,
                "local_url": url_for("static", filename=f"uploads/videos/{unique_name}")
            })

    return jsonify({"success": True, "uploaded": results, "count": len(results)})


@app.route("/admin/api/cloud-storage/delete", methods=["POST"])
@login_required
def api_cloud_storage_delete():
    data = request.get_json(silent=True) or request.form
    filename = data.get("filename")
    folder = data.get("folder")
    file_id = data.get("id")

    if not filename and not file_id:
        return jsonify({"error": "Missing filename or id"}), 400

    db = get_db()
    deleted = False

    if folder == "photos" or not folder:
        row = None
        if file_id:
            row = db.execute("SELECT * FROM photos WHERE id = ?", (file_id,)).fetchone()
        elif filename:
            row = db.execute("SELECT * FROM photos WHERE filename = ?", (filename,)).fetchone()

        if row:
            path = os.path.join(PHOTO_DIR, row["filename"])
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            delete_file_from_firebase("photos", row["filename"])
            if FIREBASE_DB:
                try:
                    FIREBASE_DB.collection("photos").document(row["filename"]).delete()
                except Exception:
                    pass
            db.execute("DELETE FROM photos WHERE id = ?", (row["id"],))
            db.commit()
            deleted = True

    if (folder == "videos" or not folder) and not deleted:
        row = None
        if file_id:
            row = db.execute("SELECT * FROM videos WHERE id = ?", (file_id,)).fetchone()
        elif filename:
            row = db.execute("SELECT * FROM videos WHERE filename = ?", (filename,)).fetchone()

        if row:
            if row["filename"]:
                path = os.path.join(VIDEO_DIR, row["filename"])
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                delete_file_from_firebase("videos", row["filename"])
                if FIREBASE_DB:
                    try:
                        FIREBASE_DB.collection("videos").document(row["filename"]).delete()
                    except Exception:
                        pass
            db.execute("DELETE FROM videos WHERE id = ?", (row["id"],))
            db.commit()
            deleted = True

    return jsonify({"success": deleted})


@app.route("/admin/api/cloud-storage/sync", methods=["POST"])
@login_required
def api_cloud_storage_sync():
    if not FIREBASE_BUCKET:
        return jsonify({"error": "Firebase Storage is not connected. Add valid firebase_key.json credentials."}), 400

    db = get_db()
    photos = db.execute("SELECT * FROM photos").fetchall()
    videos = db.execute("SELECT * FROM videos").fetchall()

    synced_photos = 0
    synced_videos = 0

    for p in photos:
        if not p.get("cloud_url"):
            loc = os.path.join(PHOTO_DIR, p["filename"])
            if os.path.exists(loc):
                c_url = upload_file_to_firebase(loc, "photos", p["filename"])
                if c_url:
                    db.execute("UPDATE photos SET cloud_url = ? WHERE id = ?", (c_url, p["id"]))
                    synced_photos += 1

    for v in videos:
        if v["filename"] and not v.get("cloud_url"):
            loc = os.path.join(VIDEO_DIR, v["filename"])
            if os.path.exists(loc):
                c_url = upload_file_to_firebase(loc, "videos", v["filename"])
                if c_url:
                    db.execute("UPDATE videos SET cloud_url = ? WHERE id = ?", (c_url, v["id"]))
                    synced_videos += 1

    db.commit()
    return jsonify({
        "success": True,
        "synced_photos": synced_photos,
        "synced_videos": synced_videos,
        "total_synced": synced_photos + synced_videos
    })


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
    local_path = os.path.join(PHOTO_DIR, unique_name)
    file.save(local_path)

    cloud_url = upload_file_to_firebase(local_path, "photos", unique_name)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    db.execute(
        "INSERT INTO photos (filename, cloud_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?)",
        (unique_name, cloud_url, caption, category, now),
    )
    db.commit()

    if FIREBASE_DB:
        try:
            FIREBASE_DB.collection("photos").document(unique_name).set({
                "filename": unique_name,
                "cloud_url": cloud_url,
                "caption": caption,
                "category": category,
                "created_at": now,
            })
        except Exception as exc:
            app.logger.warning("Firestore photo save failed: %s", exc)

    flash("Photo uploaded successfully to local & cloud storage!")
    return redirect(url_for("admin_dashboard") + "#gallery")


@app.route("/admin/photo/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    db = get_db()
    row = db.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if row:
        path = os.path.join(PHOTO_DIR, row["filename"])
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        delete_file_from_firebase("photos", row["filename"])
        if FIREBASE_DB:
            try:
                FIREBASE_DB.collection("photos").document(row["filename"]).delete()
            except Exception as exc:
                app.logger.warning("Firestore photo delete failed: %s", exc)
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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    filename = None
    cloud_url = None

    if file and file.filename:
        if not allowed_file(file.filename, ALLOWED_VIDEO_EXT):
            flash("Unsupported video format. Use MP4, WEBM or MOV.")
            return redirect(url_for("admin_dashboard") + "#videos")
        safe = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe}"
        local_path = os.path.join(VIDEO_DIR, filename)
        file.save(local_path)
        cloud_url = upload_file_to_firebase(local_path, "videos", filename)

    if not filename and not embed_url:
        flash("Upload a video file or paste a YouTube/Instagram embed link.")
        return redirect(url_for("admin_dashboard") + "#videos")

    db = get_db()
    db.execute(
        "INSERT INTO videos (filename, cloud_url, embed_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (filename, cloud_url, embed_url, caption, category, now),
    )
    db.commit()

    if FIREBASE_DB:
        try:
            doc_id = filename or f"embed_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            FIREBASE_DB.collection("videos").document(doc_id).set({
                "filename": filename,
                "cloud_url": cloud_url,
                "embed_url": embed_url,
                "caption": caption,
                "category": category,
                "created_at": now,
            })
        except Exception as exc:
            app.logger.warning("Firestore video save failed: %s", exc)

    flash("Video added successfully!")
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
                try:
                    os.remove(path)
                except Exception:
                    pass
            delete_file_from_firebase("videos", row["filename"])
            if FIREBASE_DB:
                try:
                    FIREBASE_DB.collection("videos").document(row["filename"]).delete()
                except Exception as exc:
                    app.logger.warning("Firestore video delete failed: %s", exc)
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
    init_firebase()
    app.run(debug=True, host="0.0.0.0", port=5000)
else:
    init_db()
    init_firebase()
