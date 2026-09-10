# FA Events — Website

A complete website for FA Events (event & wedding decoration, Parvathipuram /
Nagercoil / Kanyakumari District), built with **Python (Flask) + HTML + CSS +
JavaScript**, with a SQLite database.

## What's included

- **Public website** — home, about, services, photo gallery, video gallery,
  customer reviews with a 5-star rating widget, and a contact/enquiry form.
  Includes local SEO: meta titles/descriptions, `robots.txt`, `sitemap.xml`,
  and `LocalBusiness` structured data (JSON-LD) for Google.
- **Admin dashboard** (`/admin`) — protected by login. The owner can:
  - View and manage customer enquiries (mark read / delete). A badge shows
    unread count.
  - Upload and delete photos and videos (or paste a YouTube/Instagram embed
    link) — no code changes needed.
  - Approve or delete customer star ratings/reviews before they go public.
  - Change the admin password.
- **Visitor notification** — new enquiries always appear instantly in the
  admin dashboard (unread badge). Optional email notification can be turned
  on — see "Email notifications" below.
- **Ratings** — visitors submit a name + star rating (1–5) + optional
  comment. New ratings are held as "pending" until the owner approves them
  in the dashboard, so only real reviews go live. The homepage shows the
  live average rating and total review count.

## 1. Run it locally

```bash
cd fa-events
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

The database (`faevents.db`) and an admin account are created automatically
the first time you run the app.

**Default admin login:**
- URL: `http://127.0.0.1:5000/admin/login`
- Username: `admin`
- Password: `faevents2026`

⚠️ **Log in and change this password immediately** from Admin → Settings.

## 2. Update your business details

Open `app.py` and edit the `BUSINESS` dictionary near the top: phone number,
WhatsApp number, WhatsApp group invite link, Instagram link, email, address,
and the Google Maps embed link. These values automatically appear
everywhere on the site (header, footer, contact section, structured data).

To get your Google Maps embed link: open Google Maps → search your
location → Share → Embed a map → copy the `src="..."` URL and paste it into
`map_embed_src`.

## 3. Add your real photos and videos

Once logged into `/admin`, use the **Photo Gallery** and **Video Gallery**
panels to upload images (JPG/PNG/WEBP/GIF) and either upload a video file
(MP4/WEBM/MOV) or paste a YouTube/Instagram embed link. Add a caption and a
category (e.g. "Wedding", "Birthday", "Stage") — categories automatically
become filter tabs on the public gallery.

## 4. Email notifications (optional)

By default, new enquiries show up instantly in the admin dashboard, which
is enough on its own — no configuration needed. If you'd also like an email
sent to the owner for every enquiry, set these environment variables before
running the app:

```bash
export FA_SMTP_HOST=smtp.gmail.com
export FA_SMTP_PORT=587
export FA_SMTP_USER=your-gmail-address@gmail.com
export FA_SMTP_PASS=your-gmail-app-password   # use a Gmail "App Password", not your normal password
export FA_OWNER_EMAIL=faevents.enquiry@gmail.com
```

If these are not set, email notification is simply skipped — nothing
breaks, and enquiries are never lost since they're always saved to the
database.

## 5. Security notes before going live

- Change the default admin password (Settings tab).
- Set a strong, random `FA_SECRET_KEY` environment variable in production
  (used to secure login sessions):
  ```bash
  export FA_SECRET_KEY="a-long-random-string"
  ```
- Never commit `faevents.db` (customer data) to a public GitHub repo.
- The admin area (`/admin*`) is excluded from search engines via
  `noindex, nofollow` meta tags and is protected by a login — customer
  enquiry data is never publicly accessible.

## 6. Deploying online

This is a standard Flask app, so it deploys to any Python host — Render,
Railway, PythonAnywhere, or a VPS. General steps:

1. Push the project to GitHub (add a `.gitignore` for `faevents.db`,
   `venv/`, and uploaded files if you don't want them in git).
2. On your host, set the environment variables from steps 2 and 4 above.
3. Set the start command to `gunicorn app:app` (add `gunicorn` to
   `requirements.txt` for production) or `python app.py` for simple hosts.
4. Point your domain (e.g. `faevents.in`) at the host, and update
   `canonical`/`og:url` expectations by simply visiting the live domain —
   they're generated automatically from the request URL.
5. After going live, add the site to **Google Search Console** and submit
   `https://yourdomain/sitemap.xml`, and create/claim your **Google
   Business Profile** with the same name, address and phone number used in
   `app.py` for the strongest local SEO results.

## Project structure

```
fa-events/
├── app.py                     # Flask app: routes, database, auth, notifications
├── requirements.txt
├── faevents.db                 # created automatically on first run
├── templates/
│   ├── index.html              # public website
│   ├── admin_login.html
│   └── admin_dashboard.html
└── static/
    ├── css/style.css
    ├── js/main.js
    └── uploads/
        ├── photos/             # uploaded via admin dashboard
        └── videos/
```
