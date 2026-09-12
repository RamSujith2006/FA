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
import urllib.parse
import threading
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
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

if IS_VERCEL:
    DB_PATH = "/tmp/faevents.db"
    PHOTO_DIR = "/tmp/photos"
    VIDEO_DIR = "/tmp/videos"
else:
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
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_URL:
    try:
        parsed_c = urllib.parse.urlparse(CLOUDINARY_URL)
        if parsed_c.username:
            CLOUDINARY_API_KEY = parsed_c.username
        if parsed_c.password:
            CLOUDINARY_API_SECRET = parsed_c.password
        if parsed_c.hostname:
            CLOUDINARY_CLOUD_NAME = parsed_c.hostname
    except Exception as exc:
        print(f"[Cloudinary Parse Error]: {exc}")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.utils
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True
        )
        HAS_CLOUDINARY = True
        print(f"[Cloudinary Storage] Connected successfully! Cloud Name: {CLOUDINARY_CLOUD_NAME}")
    except Exception as exc:
        print(f"[Cloudinary Storage] Notice: {exc}")

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "heic"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov", "m4v", "mkv", "avi", "3gp", "flv", "wmv"}
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
    cred_json_env = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")

    if not cred_path and not cred_json_env:
        for p in [os.path.join(BASE_DIR, "firebase_key.json.json"), os.path.join(BASE_DIR, "firebase_key.json")]:
            if os.path.exists(p):
                cred_path = p
                break

    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage

        cred = None
        if cred_json_env:
            try:
                cred_dict = json.loads(cred_json_env)
                if not bucket_name:
                    project_id = cred_dict.get("project_id")
                    if project_id:
                        bucket_name = f"{project_id}.appspot.com"
                cred = credentials.Certificate(cred_dict)
            except Exception as e:
                print(f"[Firebase JSON Env Error]: {e}")

        if not cred and cred_path and os.path.exists(cred_path):
            if not bucket_name:
                try:
                    with open(cred_path, "r", encoding="utf-8") as f:
                        cred_data = json.load(f)
                        project_id = cred_data.get("project_id")
                        if project_id:
                            bucket_name = f"{project_id}.appspot.com"
                except Exception:
                    pass
            cred = credentials.Certificate(cred_path)

        if cred:
            if not firebase_admin._apps:
                options = {"storageBucket": bucket_name} if bucket_name else {}
                firebase_admin.initialize_app(cred, options)

            FIREBASE_DB = None  # Disabled Firestore API connection to prevent 403 gRPC timeouts
            if bucket_name:
                FIREBASE_BUCKET = storage.bucket(bucket_name)
                FIREBASE_BUCKET_NAME = bucket_name
            else:
                FIREBASE_BUCKET = storage.bucket()
                FIREBASE_BUCKET_NAME = FIREBASE_BUCKET.name if FIREBASE_BUCKET else "Default Bucket"
            print(f"[Firebase Storage] Connected to Cloud Storage! Bucket: {FIREBASE_BUCKET_NAME}")
    except Exception as exc:
        print(f"[Firebase Storage] Notice: {exc}")


def delete_file_from_cloud(folder, filename=None, cloud_url=None):
    if HAS_CLOUDINARY:
        try:
            import cloudinary.uploader

            possible_ids = set()
            if cloud_url and "fa-events/" in cloud_url:
                after = cloud_url.split("fa-events/")[-1]
                possible_ids.add("fa-events/" + after)
                possible_ids.add("fa-events/" + after.rsplit(".", 1)[0])
            if filename:
                possible_ids.add(f"fa-events/{folder}/{filename}")
                possible_ids.add(f"fa-events/{folder}/{filename.rsplit('.', 1)[0]}")

            res_types = ["image", "video", "raw"]
            for pid in possible_ids:
                for rtype in res_types:
                    try:
                        res = cloudinary.uploader.destroy(pid, resource_type=rtype)
                        if res.get("result") == "ok":
                            print(f"[Cloudinary Storage Delete]: {pid} ({rtype}) -> ok")
                    except Exception:
                        pass
        except Exception as exc:
            app.logger.warning("Cloudinary delete warning: %s", exc)

    if FIREBASE_BUCKET and filename:
        try:
            blob_name = f"{folder}/{filename}"
            blob = FIREBASE_BUCKET.blob(blob_name)
            if blob.exists():
                blob.delete()
                print(f"[Firebase Storage Delete]: {blob_name}")
        except Exception as exc:
            app.logger.warning("Firebase Storage delete failed: %s", exc)


LAST_FIRESTORE_SYNC = 0

def push_enquiries_to_cloud(db, allow_empty=False):
    try:
        rows = db.execute("SELECT * FROM enquiries ORDER BY id ASC").fetchall()
        data = [dict(r) for r in rows]
        if not data and not allow_empty:
            print("[Push Enquiries Notice]: Local DB is empty, skipping cloud overwrite to protect long-term storage.")
            return

        if HAS_CLOUDINARY:
            try:
                import cloudinary.uploader
                cloudinary.uploader.upload(
                    json.dumps(data).encode("utf-8"),
                    folder="fa-events/data",
                    public_id="enquiries.json",
                    resource_type="raw",
                    overwrite=True,
                    invalidate=True
                )
            except Exception as exc:
                print(f"[Cloudinary Enquiries Push Error]: {exc}")

        if FIREBASE_DB:
            for item in data:
                try:
                    FIREBASE_DB.collection("enquiries").document(str(item["id"])).set(item)
                except Exception:
                    pass
    except Exception as exc:
        print(f"[Push Enquiries Error]: {exc}")


def push_ratings_to_cloud(db, allow_empty=False):
    try:
        rows = db.execute("SELECT * FROM ratings ORDER BY id ASC").fetchall()
        data = [dict(r) for r in rows]
        if not data and not allow_empty:
            print("[Push Ratings Notice]: Local DB is empty, skipping cloud overwrite to protect long-term storage.")
            return

        if HAS_CLOUDINARY:
            try:
                import cloudinary.uploader
                cloudinary.uploader.upload(
                    json.dumps(data).encode("utf-8"),
                    folder="fa-events/data",
                    public_id="ratings.json",
                    resource_type="raw",
                    overwrite=True,
                    invalidate=True
                )
            except Exception as exc:
                print(f"[Cloudinary Ratings Push Error]: {exc}")

        if FIREBASE_DB:
            for item in data:
                try:
                    FIREBASE_DB.collection("ratings").document(str(item["id"])).set(item)
                except Exception:
                    pass
    except Exception as exc:
        print(f"[Push Ratings Error]: {exc}")


def sync_enquiries_from_cloud(db, deleted_set=None):
    if deleted_set is None:
        deleted_set = set()
        try:
            rows_del = db.execute("SELECT identifier FROM deleted_items WHERE item_type = 'enquiry'").fetchall()
            deleted_set = {r["identifier"] for r in rows_del if r["identifier"]}
        except Exception:
            pass

    enquiries_list = []

    if HAS_CLOUDINARY and CLOUDINARY_CLOUD_NAME:
        try:
            import urllib.request
            cb = int(datetime.now().timestamp())
            raw_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/raw/upload/fa-events/data/enquiries.json?_cb={cb}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "FAEventsApp/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    enquiries_list = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

    if not enquiries_list and FIREBASE_DB:
        try:
            e_docs = FIREBASE_DB.collection("enquiries").stream()
            for doc in e_docs:
                d = doc.to_dict()
                if d:
                    enquiries_list.append(d)
        except Exception:
            pass

    for d in enquiries_list:
        if not d:
            continue
        name = (d.get("name") or "").strip()
        phone = (d.get("phone") or "").strip()
        email = (d.get("email") or "").strip()
        event_type = (d.get("event_type") or "").strip()
        event_date = (d.get("event_date") or "").strip()
        location = (d.get("location") or "").strip()
        message = (d.get("message") or "").strip()
        created_at = d.get("created_at") or "2026-01-01 00:00:00"
        is_read = 1 if d.get("is_read") else 0
        item_id = d.get("id")

        del_id1 = f"enquiry_{created_at}_{phone}"
        del_id2 = f"enquiry_{item_id}" if item_id else None

        if del_id1 in deleted_set or (del_id2 and del_id2 in deleted_set):
            if item_id:
                db.execute("DELETE FROM enquiries WHERE id = ?", (item_id,))
            continue

        existing = None
        if item_id:
            existing = db.execute("SELECT id FROM enquiries WHERE id = ?", (item_id,)).fetchone()
        if not existing and phone and name:
            existing = db.execute("SELECT id FROM enquiries WHERE phone = ? AND name = ? AND created_at = ?", (phone, name, created_at)).fetchone()

        if not existing:
            if item_id:
                db.execute(
                    "INSERT INTO enquiries (id, name, phone, email, event_type, event_date, location, message, created_at, is_read) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (item_id, name, phone, email, event_type, event_date, location, message, created_at, is_read)
                )
            else:
                db.execute(
                    "INSERT INTO enquiries (name, phone, email, event_type, event_date, location, message, created_at, is_read) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, phone, email, event_type, event_date, location, message, created_at, is_read)
                )
        else:
            db.execute("UPDATE enquiries SET name = ?, phone = ?, email = ?, event_type = ?, event_date = ?, location = ?, message = ?, created_at = ?, is_read = ? WHERE id = ?",
                       (name, phone, email, event_type, event_date, location, message, created_at, is_read, existing["id"]))

    db.commit()


def sync_ratings_from_cloud(db, deleted_set=None):
    if deleted_set is None:
        deleted_set = set()
        try:
            rows_del = db.execute("SELECT identifier FROM deleted_items WHERE item_type = 'rating'").fetchall()
            deleted_set = {r["identifier"] for r in rows_del if r["identifier"]}
        except Exception:
            pass

    ratings_list = []

    if HAS_CLOUDINARY and CLOUDINARY_CLOUD_NAME:
        try:
            import urllib.request
            cb = int(datetime.now().timestamp())
            raw_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/raw/upload/fa-events/data/ratings.json?_cb={cb}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "FAEventsApp/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    ratings_list = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

    if not ratings_list and FIREBASE_DB:
        try:
            r_docs = FIREBASE_DB.collection("ratings").stream()
            for doc in r_docs:
                d = doc.to_dict()
                if d:
                    ratings_list.append(d)
        except Exception:
            pass

    for d in ratings_list:
        if not d:
            continue
        name = (d.get("name") or "").strip()
        stars = d.get("stars", 5)
        try:
            stars = int(stars)
        except (ValueError, TypeError):
            stars = 5
        comment = (d.get("comment") or "").strip()
        created_at = d.get("created_at") or "2026-01-01 00:00:00"
        approved = 1 if d.get("approved") else 0
        item_id = d.get("id")

        del_id1 = f"rating_{created_at}_{name}"
        del_id2 = f"rating_{item_id}" if item_id else None

        if del_id1 in deleted_set or (del_id2 and del_id2 in deleted_set):
            if item_id:
                db.execute("DELETE FROM ratings WHERE id = ?", (item_id,))
            continue

        existing = None
        if item_id:
            existing = db.execute("SELECT id FROM ratings WHERE id = ?", (item_id,)).fetchone()
        if not existing and name:
            existing = db.execute("SELECT id FROM ratings WHERE name = ? AND created_at = ?", (name, created_at)).fetchone()

        if not existing:
            if item_id:
                db.execute(
                    "INSERT INTO ratings (id, name, stars, comment, created_at, approved) VALUES (?, ?, ?, ?, ?, ?)",
                    (item_id, name, stars, comment, created_at, approved)
                )
            else:
                db.execute(
                    "INSERT INTO ratings (name, stars, comment, created_at, approved) VALUES (?, ?, ?, ?, ?)",
                    (name, stars, comment, created_at, approved)
                )
        else:
            db.execute("UPDATE ratings SET name = ?, stars = ?, comment = ?, created_at = ?, approved = ? WHERE id = ?",
                       (name, stars, comment, created_at, approved, existing["id"]))

    db.commit()


def push_deleted_items_to_cloud(db):
    try:
        rows = db.execute("SELECT * FROM deleted_items ORDER BY id ASC").fetchall()
        data = [dict(r) for r in rows]

        if HAS_CLOUDINARY:
            try:
                import cloudinary.uploader
                cloudinary.uploader.upload(
                    json.dumps(data).encode("utf-8"),
                    folder="fa-events/data",
                    public_id="deleted_items.json",
                    resource_type="raw",
                    overwrite=True,
                    invalidate=True
                )
            except Exception as exc:
                print(f"[Cloudinary Deleted Items Push Error]: {exc}")
    except Exception as exc:
        print(f"[Push Deleted Items Error]: {exc}")


def push_photos_to_cloud(db, allow_empty=False):
    try:
        rows = db.execute("SELECT * FROM photos ORDER BY id ASC").fetchall()
        data = [dict(r) for r in rows]
        if not data and not allow_empty:
            print("[Push Photos Notice]: Local DB is empty, skipping cloud overwrite to protect long-term storage.")
            return

        if HAS_CLOUDINARY:
            try:
                import cloudinary.uploader
                cloudinary.uploader.upload(
                    json.dumps(data).encode("utf-8"),
                    folder="fa-events/data",
                    public_id="photos.json",
                    resource_type="raw",
                    overwrite=True,
                    invalidate=True
                )
            except Exception as exc:
                print(f"[Cloudinary Photos Push Error]: {exc}")
    except Exception as exc:
        print(f"[Push Photos Error]: {exc}")


def push_videos_to_cloud(db, allow_empty=False):
    try:
        rows = db.execute("SELECT * FROM videos ORDER BY id ASC").fetchall()
        data = [dict(r) for r in rows]
        if not data and not allow_empty:
            print("[Push Videos Notice]: Local DB is empty, skipping cloud overwrite to protect long-term storage.")
            return

        if HAS_CLOUDINARY:
            try:
                import cloudinary.uploader
                cloudinary.uploader.upload(
                    json.dumps(data).encode("utf-8"),
                    folder="fa-events/data",
                    public_id="videos.json",
                    resource_type="raw",
                    overwrite=True,
                    invalidate=True
                )
            except Exception as exc:
                print(f"[Cloudinary Videos Push Error]: {exc}")
    except Exception as exc:
        print(f"[Push Videos Error]: {exc}")


import re

def normalize_media_identifier(ident):
    if not ident:
        return set()
    ident = str(ident).strip()
    if not ident:
        return set()

    variations = {ident, ident.lower()}
    
    basename = ident.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].split("?")[0]
    if basename:
        variations.add(basename)
        variations.add(basename.lower())
        if "." in basename:
            no_ext = basename.rsplit(".", 1)[0]
            variations.add(no_ext)
            variations.add(no_ext.lower())

    no_ver = re.sub(r'/v\d+/', '/', ident)
    variations.add(no_ver)
    variations.add(no_ver.lower())

    no_proto = re.sub(r'^https?://', '', ident)
    variations.add(no_proto)
    variations.add(no_proto.lower())

    no_proto_ver = re.sub(r'/v\d+/', '/', no_proto)
    variations.add(no_proto_ver)
    variations.add(no_proto_ver.lower())

    return variations


def is_item_deleted(deleted_set, fn=None, cloud_url=None, embed_url=None, public_id=None):
    if not deleted_set:
        return False

    targets = set()
    for item in (fn, cloud_url, embed_url, public_id):
        if item:
            targets.update(normalize_media_identifier(item))

    if not targets:
        return False

    normalized_deleted = set()
    for d in deleted_set:
        normalized_deleted.update(normalize_media_identifier(d))

    return bool(targets.intersection(normalized_deleted))


def sync_deleted_items_from_cloud(db):
    deleted_list = []
    if HAS_CLOUDINARY and CLOUDINARY_CLOUD_NAME:
        try:
            import urllib.request
            cb = int(datetime.now().timestamp())
            raw_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/raw/upload/fa-events/data/deleted_items.json?_cb={cb}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "FAEventsApp/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    deleted_list = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

    for d in deleted_list:
        if not d or not d.get("identifier"):
            continue
        item_type = d.get("item_type", "unknown")
        identifier = d.get("identifier")
        created_at = d.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            db.execute(
                "INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES (?, ?, ?)",
                (item_type, identifier, created_at)
            )
        except Exception:
            pass
    db.commit()


def sync_photos_from_cloud(db, deleted_set=None):
    if deleted_set is None:
        deleted_set = set()
        try:
            rows_del = db.execute("SELECT identifier FROM deleted_items").fetchall()
            deleted_set = {r["identifier"] for r in rows_del if r["identifier"]}
        except Exception:
            pass

    photos_list = []
    if HAS_CLOUDINARY and CLOUDINARY_CLOUD_NAME:
        try:
            import urllib.request
            cb = int(datetime.now().timestamp())
            raw_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/raw/upload/fa-events/data/photos.json?_cb={cb}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "FAEventsApp/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    photos_list = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

    for d in photos_list:
        if not d:
            continue
        fn = d.get("filename", "")
        cloud_url = d.get("cloud_url", "")
        caption = d.get("caption", "")
        category = d.get("category", "")
        created_at = d.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_item_deleted(deleted_set, fn=fn, cloud_url=cloud_url):
            if fn or cloud_url:
                db.execute("DELETE FROM photos WHERE filename = ? OR (cloud_url IS NOT NULL AND cloud_url != '' AND cloud_url = ?)", (fn, cloud_url))
            continue

        existing = db.execute("SELECT id FROM photos WHERE filename = ? OR (cloud_url IS NOT NULL AND cloud_url != '' AND cloud_url = ?)", (fn, cloud_url)).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO photos (filename, cloud_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?)",
                (fn, cloud_url, caption, category, created_at)
            )
        else:
            db.execute(
                "UPDATE photos SET cloud_url = ?, caption = ?, category = ?, created_at = ? WHERE id = ?",
                (cloud_url, caption, category, created_at, existing["id"])
            )
    db.commit()


def sync_videos_from_cloud(db, deleted_set=None):
    if deleted_set is None:
        deleted_set = set()
        try:
            rows_del = db.execute("SELECT identifier FROM deleted_items").fetchall()
            deleted_set = {r["identifier"] for r in rows_del if r["identifier"]}
        except Exception:
            pass

    videos_list = []
    if HAS_CLOUDINARY and CLOUDINARY_CLOUD_NAME:
        try:
            import urllib.request
            cb = int(datetime.now().timestamp())
            raw_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/raw/upload/fa-events/data/videos.json?_cb={cb}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "FAEventsApp/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    videos_list = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

    for d in videos_list:
        if not d:
            continue
        fn = d.get("filename", "")
        cloud_url = d.get("cloud_url", "")
        embed_url = d.get("embed_url", "")
        caption = d.get("caption", "")
        category = d.get("category", "")
        created_at = d.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_item_deleted(deleted_set, fn=fn, cloud_url=cloud_url, embed_url=embed_url):
            if cloud_url:
                db.execute("DELETE FROM videos WHERE cloud_url = ?", (cloud_url,))
            if fn:
                db.execute("DELETE FROM videos WHERE filename = ?", (fn,))
            if embed_url:
                db.execute("DELETE FROM videos WHERE embed_url = ?", (embed_url,))
            continue

        existing = None
        if cloud_url:
            existing = db.execute("SELECT id FROM videos WHERE cloud_url = ?", (cloud_url,)).fetchone()
        elif fn:
            existing = db.execute("SELECT id FROM videos WHERE filename = ?", (fn,)).fetchone()
        elif embed_url:
            existing = db.execute("SELECT id FROM videos WHERE embed_url = ?", (embed_url,)).fetchone()

        if not existing:
            db.execute(
                "INSERT INTO videos (filename, cloud_url, embed_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (fn, cloud_url, embed_url, caption, category, created_at)
            )
        else:
            db.execute(
                "UPDATE videos SET filename = ?, cloud_url = ?, embed_url = ?, caption = ?, category = ?, created_at = ? WHERE id = ?",
                (fn, cloud_url, embed_url, caption, category, created_at, existing["id"])
            )
    db.commit()


def sync_from_firestore_to_sqlite(db, force=False):
    global LAST_FIRESTORE_SYNC

    now_ts = datetime.now().timestamp()

    # Rate limit: sync at most once every 3 seconds to prevent double-clicks while keeping data fresh
    if not force and (now_ts - LAST_FIRESTORE_SYNC < 3):
        return

    LAST_FIRESTORE_SYNC = now_ts

    # 1. Always sync deleted_items blacklist from Cloud Storage first
    sync_deleted_items_from_cloud(db)

    # Fetch updated blacklist of deleted item identifiers
    deleted_set = set()
    try:
        rows_del = db.execute("SELECT identifier FROM deleted_items").fetchall()
        deleted_set = {r["identifier"] for r in rows_del if r["identifier"]}
    except Exception:
        pass

    # 2. Sync enquiries & ratings (fast)
    sync_enquiries_from_cloud(db, deleted_set=deleted_set)
    sync_ratings_from_cloud(db, deleted_set=deleted_set)

    # 3. Always sync photos & videos to keep dashboard 100% accurate
    sync_photos_from_cloud(db, deleted_set=deleted_set)
    sync_videos_from_cloud(db, deleted_set=deleted_set)

    LAST_FIRESTORE_SYNC = now_ts



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

        CREATE TABLE IF NOT EXISTS deleted_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            identifier TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
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
    sync_from_firestore_to_sqlite(db)
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
        total_ratings=total_reviews,
    )


@app.route("/enquire", methods=["POST"])
def submit_enquiry():
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              "application/json" in request.headers.get("Accept", "") or \
              request.is_json or \
              request.headers.get("Sec-Fetch-Mode") == "cors"

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    event_type = request.form.get("event_type", "").strip()
    event_date = request.form.get("event_date", "").strip()
    location = request.form.get("location", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not phone:
        if is_ajax:
            return jsonify({"ok": False, "error": "Please provide your name and phone number."})
        flash("Please provide your name and phone number.")
        return redirect(url_for("index") + "#contact")

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = get_db()
        sync_enquiries_from_cloud(db)
        cursor = db.execute(
            """
            INSERT INTO enquiries (name, phone, email, event_type, event_date, location, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, phone, email, event_type, event_date, location, message, now),
        )
        db.commit()
        enquiry_id = cursor.lastrowid

        push_enquiries_to_cloud(db)

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
    except Exception as exc:
        app.logger.error("Enquiry save error: %s", exc)
        if is_ajax:
            return jsonify({"ok": False, "error": "Could not save enquiry. Please try again."}), 500

    if is_ajax:
        return jsonify({"ok": True, "message": "Thank you! Your enquiry has been sent. We will call you back shortly."})

    flash("Thank you! Your enquiry has been sent. We will call you back shortly.")
    return redirect(url_for("index") + "#contact")


@app.route("/rating/submit", methods=["POST"])
def submit_rating():
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              "application/json" in request.headers.get("Accept", "") or \
              request.is_json or \
              request.headers.get("Sec-Fetch-Mode") == "cors"

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
        if is_ajax:
            return jsonify({"ok": False, "error": "Please enter your name for the review."})
        flash("Please enter your name for the review.")
        return redirect(url_for("index") + "#reviews")

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = get_db()
        sync_ratings_from_cloud(db)
        cursor = db.execute(
            "INSERT INTO ratings (name, stars, comment, created_at, approved) VALUES (?, ?, ?, ?, 0)",
            (name, stars_int, comment, now),
        )
        db.commit()
        rating_id = cursor.lastrowid

        push_ratings_to_cloud(db)

        if FIREBASE_DB:
            try:
                FIREBASE_DB.collection("ratings").document(str(rating_id)).set({
                    "id": rating_id,
                    "name": name,
                    "stars": stars_int,
                    "comment": comment,
                    "created_at": now,
                    "approved": False,
                })
            except Exception as exc:
                app.logger.warning("Firestore rating save failed: %s", exc)
    except Exception as exc:
        app.logger.error("Rating save error: %s", exc)
        if is_ajax:
            return jsonify({"ok": False, "error": "Could not submit review. Please try again."}), 500

    if is_ajax:
        return jsonify({"ok": True, "message": "Thank you for your rating! It will appear on the website once approved by our team."})

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


def bg_cloud_sync(action_type, **kwargs):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.row_factory = sqlite3.Row
            if action_type == "delete_photo":
                fn = kwargs.get("fn")
                c_url = kwargs.get("c_url")
                delete_file_from_cloud("photos", fn, cloud_url=c_url)
                if FIREBASE_DB and fn:
                    try:
                        FIREBASE_DB.collection("photos").document(fn).delete()
                    except Exception:
                        pass
                push_photos_to_cloud(db, allow_empty=True)
                push_deleted_items_to_cloud(db)

            elif action_type == "delete_video":
                fn = kwargs.get("fn")
                c_url = kwargs.get("c_url")
                embed = kwargs.get("embed")
                video_id = kwargs.get("video_id")
                delete_file_from_cloud("videos", fn, cloud_url=c_url)
                if FIREBASE_DB:
                    try:
                        doc_id = fn or embed or str(video_id)
                        FIREBASE_DB.collection("videos").document(doc_id).delete()
                    except Exception:
                        pass
                push_videos_to_cloud(db, allow_empty=True)
                push_deleted_items_to_cloud(db)

            elif action_type == "delete_enquiry":
                enquiry_id = kwargs.get("enquiry_id")
                push_enquiries_to_cloud(db, allow_empty=True)
                push_deleted_items_to_cloud(db)
                if FIREBASE_DB and enquiry_id:
                    try:
                        FIREBASE_DB.collection("enquiries").document(str(enquiry_id)).delete()
                    except Exception:
                        pass

            elif action_type == "delete_rating":
                rating_id = kwargs.get("rating_id")
                push_ratings_to_cloud(db, allow_empty=True)
                push_deleted_items_to_cloud(db)
                if FIREBASE_DB and rating_id:
                    try:
                        FIREBASE_DB.collection("ratings").document(str(rating_id)).delete()
                    except Exception:
                        pass
    except Exception as exc:
        print(f"[Cloud Sync Error]: {exc}")


def delete_file_from_cloud(folder, filename=None, cloud_url=None):
    # 1. Delete from Cloudinary Cloud Storage
    if HAS_CLOUDINARY:
        try:
            import cloudinary.uploader
            
            possible_ids = set()
            if cloud_url and "fa-events/" in cloud_url:
                after = cloud_url.split("fa-events/")[-1]
                possible_ids.add("fa-events/" + after.rsplit(".", 1)[0])
            if filename:
                fn_no_ext = filename.rsplit(".", 1)[0]
                possible_ids.add(f"fa-events/{folder}/{fn_no_ext}")

            primary_rtype = "video" if folder == "videos" else "image"
            res_types = [primary_rtype, "raw", "image" if primary_rtype == "video" else "video"]

            for pid in possible_ids:
                for rtype in res_types:
                    try:
                        res = cloudinary.uploader.destroy(pid, resource_type=rtype)
                        if res.get("result") == "ok":
                            print(f"[Cloudinary Storage Delete]: {pid} ({rtype}) -> ok")
                            break
                    except Exception:
                        pass
        except Exception as exc:
            app.logger.warning("Cloudinary delete warning: %s", exc)

    # 2. Delete from Firebase Storage
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
    sync_from_firestore_to_sqlite(db)
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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if folder == "photos" or not folder:
        row = None
        if file_id:
            row = db.execute("SELECT * FROM photos WHERE id = ?", (file_id,)).fetchone()
        elif filename:
            row = db.execute("SELECT * FROM photos WHERE filename = ?", (filename,)).fetchone()

        if row:
            c_url = row["cloud_url"] if "cloud_url" in row.keys() else None
            fn = row["filename"]
            if c_url:
                db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('photo', ?, ?)", (c_url, now))
            if fn:
                db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('photo', ?, ?)", (fn, now))

            path = os.path.join(PHOTO_DIR, fn) if fn else None
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            delete_file_from_cloud("photos", fn, cloud_url=c_url)
            if FIREBASE_DB and fn:
                try:
                    FIREBASE_DB.collection("photos").document(fn).delete()
                except Exception:
                    pass
            db.execute("DELETE FROM photos WHERE id = ?", (row["id"],))
            db.commit()
            bg_cloud_sync("delete_photo", fn=fn, c_url=c_url)
            deleted = True

    if (folder == "videos" or not folder) and not deleted:
        row = None
        if file_id:
            row = db.execute("SELECT * FROM videos WHERE id = ?", (file_id,)).fetchone()
        elif filename:
            row = db.execute("SELECT * FROM videos WHERE filename = ?", (filename,)).fetchone()

        if row:
            c_url = row["cloud_url"] if "cloud_url" in row.keys() else None
            fn = row["filename"]
            embed = row["embed_url"] if "embed_url" in row.keys() else None

            if c_url:
                db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('video', ?, ?)", (c_url, now))
            if fn:
                db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('video', ?, ?)", (fn, now))
            if embed:
                db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('video', ?, ?)", (embed, now))

            if fn:
                path = os.path.join(VIDEO_DIR, fn)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            db.execute("DELETE FROM videos WHERE id = ?", (row["id"],))
            db.commit()
            bg_cloud_sync("delete_video", fn=fn, c_url=c_url, embed=embed, video_id=row["id"])
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
    push_photos_to_cloud(db)
    push_videos_to_cloud(db)
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
    sync_enquiries_from_cloud(db)
    db.execute("UPDATE enquiries SET is_read = 1 WHERE id = ?", (enquiry_id,))
    db.commit()
    push_enquiries_to_cloud(db)
    if FIREBASE_DB:
        try:
            FIREBASE_DB.collection("enquiries").document(str(enquiry_id)).set({"is_read": True}, merge=True)
        except Exception:
            pass
    return redirect(url_for("admin_dashboard") + "#enquiries")


@app.route("/admin/enquiry/<int:enquiry_id>/delete", methods=["POST"])
@login_required
def delete_enquiry(enquiry_id):
    db = get_db()
    sync_enquiries_from_cloud(db)
    row = db.execute("SELECT * FROM enquiries WHERE id = ?", (enquiry_id,)).fetchone()
    if row:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        del_ids = [
            f"enquiry_{row['created_at']}_{row['phone']}",
            f"enquiry_{row['id']}"
        ]
        for d_id in del_ids:
            if d_id and d_id != "enquiry_":
                db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('enquiry', ?, ?)", (d_id, now))
        db.execute("DELETE FROM enquiries WHERE id = ?", (enquiry_id,))
        db.commit()
        push_enquiries_to_cloud(db, allow_empty=True)
        push_deleted_items_to_cloud(db)
        if FIREBASE_DB and enquiry_id:
            try:
                FIREBASE_DB.collection("enquiries").document(str(enquiry_id)).delete()
            except Exception:
                pass
    return redirect(url_for("admin_dashboard") + "#enquiries")


@app.route("/admin/api/cloudinary-sign", methods=["GET", "POST"])
@login_required
def api_cloudinary_sign():
    if not HAS_CLOUDINARY or not CLOUDINARY_API_SECRET:
        return jsonify({"error": "Cloudinary storage is not configured on server"}), 400

    folder = request.args.get("folder") or request.form.get("folder") or "videos"
    if folder not in ["photos", "videos"]:
        folder = "videos"

    timestamp = int(datetime.now().timestamp())
    target_folder = f"fa-events/{folder}"
    params_to_sign = {
        "timestamp": timestamp,
        "folder": target_folder
    }

    import cloudinary.utils
    signature = cloudinary.utils.api_sign_request(params_to_sign, CLOUDINARY_API_SECRET)

    return jsonify({
        "signature": signature,
        "timestamp": timestamp,
        "api_key": CLOUDINARY_API_KEY,
        "cloud_name": CLOUDINARY_CLOUD_NAME,
        "folder": target_folder,
        "resource_type": "video" if folder == "videos" else "image"
    })


@app.route("/admin/photo/upload", methods=["POST"])
@login_required
def upload_photo():
    file = request.files.get("photo")
    caption = request.form.get("caption", "").strip()
    category = request.form.get("category", "").strip()
    cloud_url = request.form.get("cloud_url", "").strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    unique_name = None

    if cloud_url:
        unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_photo.jpg"
    elif file and file.filename != "":
        if not allowed_file(file.filename, ALLOWED_IMAGE_EXT):
            flash("Unsupported image format. Use JPG, PNG, WEBP or GIF.")
            return redirect(url_for("admin_dashboard") + "#gallery")

        filename = secure_filename(file.filename)
        unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        local_path = os.path.join(PHOTO_DIR, unique_name)
        file.save(local_path)
        cloud_url = upload_file_to_firebase(local_path, "photos", unique_name)

        if IS_VERCEL and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass
    else:
        flash("Please choose a photo to upload.")
        return redirect(url_for("admin_dashboard") + "#gallery")

    db = get_db()
    db.execute(
        "INSERT INTO photos (filename, cloud_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?)",
        (unique_name, cloud_url, caption, category, now),
    )
    db.commit()
    push_photos_to_cloud(db)

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

    flash("Photo uploaded successfully to Cloud Storage!")
    return redirect(url_for("admin_dashboard") + "#gallery")


@app.route("/admin/photo/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    db = get_db()
    c_url = request.form.get("cloud_url", "").strip() or None
    fn = request.form.get("filename", "").strip() or None
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = db.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if not row and (c_url or fn):
        if c_url:
            row = db.execute("SELECT * FROM photos WHERE cloud_url = ?", (c_url,)).fetchone()
        if not row and fn:
            row = db.execute("SELECT * FROM photos WHERE filename = ?", (fn,)).fetchone()

    if row:
        c_url = row["cloud_url"] if "cloud_url" in row.keys() and row["cloud_url"] else c_url
        fn = row["filename"] if "filename" in row.keys() and row["filename"] else fn
        db.execute("DELETE FROM photos WHERE id = ?", (row["id"],))

    if c_url:
        db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('photo', ?, ?)", (c_url, now))
    if fn:
        db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('photo', ?, ?)", (fn, now))
        fn_no_ext = fn.rsplit(".", 1)[0]
        db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('photo', ?, ?)", (fn_no_ext, now))

    db.commit()

    if fn:
        path = os.path.join(PHOTO_DIR, fn)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    delete_file_from_cloud("photos", fn, cloud_url=c_url)
    if FIREBASE_DB and fn:
        try:
            FIREBASE_DB.collection("photos").document(fn).delete()
        except Exception:
            pass
    push_photos_to_cloud(db, allow_empty=True)
    push_deleted_items_to_cloud(db)
    flash("Photo deleted successfully.")
    return redirect(url_for("admin_dashboard") + "#gallery")


@app.route("/admin/video/upload", methods=["POST"])
@login_required
def upload_video():
    file = request.files.get("video")
    embed_url = request.form.get("embed_url", "").strip()
    caption = request.form.get("caption", "").strip()
    category = request.form.get("category", "").strip()
    cloud_url = request.form.get("cloud_url", "").strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    filename = None

    if cloud_url:
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_video.mp4"
    elif file and file.filename:
        if not allowed_file(file.filename, ALLOWED_VIDEO_EXT):
            flash("Unsupported video format. Use MP4, WEBM or MOV.")
            return redirect(url_for("admin_dashboard") + "#videos")
        safe = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe}"
        local_path = os.path.join(VIDEO_DIR, filename)
        file.save(local_path)
        cloud_url = upload_file_to_firebase(local_path, "videos", filename)

        if IS_VERCEL and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass

    if not filename and not embed_url and not cloud_url:
        flash("Upload a video file or paste a YouTube/Instagram embed link.")
        return redirect(url_for("admin_dashboard") + "#videos")

    db = get_db()
    db.execute(
        "INSERT INTO videos (filename, cloud_url, embed_url, caption, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (filename or "", cloud_url, embed_url, caption, category, now),
    )
    db.commit()
    push_videos_to_cloud(db)

    if FIREBASE_DB:
        try:
            doc_id = filename or f"embed_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            FIREBASE_DB.collection("videos").document(doc_id).set({
                "filename": filename or "",
                "cloud_url": cloud_url,
                "embed_url": embed_url,
                "caption": caption,
                "category": category,
                "created_at": now,
            })
        except Exception as exc:
            app.logger.warning("Firestore video save failed: %s", exc)

    flash("Video added successfully to Cloud Storage!")
    return redirect(url_for("admin_dashboard") + "#videos")


@app.route("/admin/video/<int:video_id>/delete", methods=["POST"])
@login_required
def delete_video(video_id):
    db = get_db()
    c_url = request.form.get("cloud_url", "").strip() or None
    fn = request.form.get("filename", "").strip() or None
    embed = request.form.get("embed_url", "").strip() or None
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = db.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
    if not row and (c_url or fn or embed):
        if c_url:
            row = db.execute("SELECT * FROM videos WHERE cloud_url = ?", (c_url,)).fetchone()
        if not row and fn:
            row = db.execute("SELECT * FROM videos WHERE filename = ?", (fn,)).fetchone()
        if not row and embed:
            row = db.execute("SELECT * FROM videos WHERE embed_url = ?", (embed,)).fetchone()

    if row:
        c_url = row["cloud_url"] if "cloud_url" in row.keys() and row["cloud_url"] else c_url
        fn = row["filename"] if "filename" in row.keys() and row["filename"] else fn
        embed = row["embed_url"] if "embed_url" in row.keys() and row["embed_url"] else embed
        db.execute("DELETE FROM videos WHERE id = ?", (row["id"],))

    if c_url:
        db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('video', ?, ?)", (c_url, now))
    if fn:
        db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('video', ?, ?)", (fn, now))
        fn_no_ext = fn.rsplit(".", 1)[0]
        db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('video', ?, ?)", (fn_no_ext, now))
    if embed:
        db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('video', ?, ?)", (embed, now))

    db.commit()

    if fn:
        path = os.path.join(VIDEO_DIR, fn)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    delete_file_from_cloud("videos", fn, cloud_url=c_url)
    if FIREBASE_DB:
        try:
            doc_id = fn or embed or str(video_id)
            FIREBASE_DB.collection("videos").document(doc_id).delete()
        except Exception:
            pass
    push_videos_to_cloud(db, allow_empty=True)
    push_deleted_items_to_cloud(db)
    flash("Video deleted successfully.")
    return redirect(url_for("admin_dashboard") + "#videos")


@app.route("/admin/rating/<int:rating_id>/approve", methods=["POST"])
@login_required
def approve_rating(rating_id):
    db = get_db()
    sync_ratings_from_cloud(db)
    db.execute("UPDATE ratings SET approved = 1 WHERE id = ?", (rating_id,))
    db.commit()
    push_ratings_to_cloud(db)
    if FIREBASE_DB:
        try:
            FIREBASE_DB.collection("ratings").document(str(rating_id)).set({"approved": True}, merge=True)
        except Exception:
            pass
    return redirect(url_for("admin_dashboard") + "#reviews")


@app.route("/admin/rating/<int:rating_id>/delete", methods=["POST"])
@login_required
def delete_rating(rating_id):
    db = get_db()
    sync_ratings_from_cloud(db)
    row = db.execute("SELECT * FROM ratings WHERE id = ?", (rating_id,)).fetchone()
    if row:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        del_ids = [
            f"rating_{row['created_at']}_{row['name']}",
            f"rating_{row['id']}"
        ]
        for d_id in del_ids:
            db.execute("INSERT OR IGNORE INTO deleted_items (item_type, identifier, created_at) VALUES ('rating', ?, ?)", (d_id, now))
        db.execute("DELETE FROM ratings WHERE id = ?", (rating_id,))
        db.commit()
        push_ratings_to_cloud(db, allow_empty=True)
        push_deleted_items_to_cloud(db)
        if FIREBASE_DB and rating_id:
            try:
                FIREBASE_DB.collection("ratings").document(str(rating_id)).delete()
            except Exception:
                pass
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
