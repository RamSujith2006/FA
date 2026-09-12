# FA Events — Media Management Website with Admin Dashboard

A modern web platform hosted on Vercel that allows administrators to easily manage photos, videos, enquiries, and reviews through a secure Admin Dashboard.

---

## Product Description

### Media Management Website with Admin Dashboard
A modern web platform hosted on **Vercel** that allows administrators to easily manage photos and videos through a secure Admin Dashboard.

### Key Features:
- 📸 **Direct Media Uploads**: Upload photos and videos from the Admin Dashboard.
- 🗑️ **On-Demand Deletion**: Delete photos and videos whenever required.
- ☁️ **Cloud Storage Integration**: Store media using Cloudinary CDN and Firebase Storage.
- 🗄️ **Multi-Tier Database Architecture**: Connect the website with SQLite and MongoDB Atlas to manage media records.
- 🔄 **Live Website Synchronization**: Automatically display newly uploaded media on the live website.
- ⚡ **Persistent Deletions**: Ensure deleted media remains deleted after page refresh without CDN or database caching leaks.
- 🔐 **Authorized Admin Access**: Secure admin-only access for upload and delete operations.
- 📱 **Responsive Design**: Fully responsive layout optimized for mobile, tablet, and desktop.

**Main Goal**: Provide a reliable and easy-to-use media management system where every upload and deletion is properly synchronized between the Admin Dashboard, database, cloud storage, and live website.

---

## System Architecture

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | Python (Flask) + HTML5 / CSS3 / Vanilla JS | High-speed request rendering, dynamic DOM interaction, and custom responsive UI. |
| **Primary Database** | SQLite (`faevents.db`) | High-speed local query engine for fast rendering (<15ms response time). |
| **Cloud Database** | MongoDB Atlas (`MONGO_URI`) | Persistent cloud database sync across Vercel serverless cold-starts. |
| **Media CDN Storage** | Cloudinary CDN | High-resolution image CDN and fast video streaming (`https://res.cloudinary.com/...`). |
| **Backup Storage** | Firebase Cloud Storage | Secondary cloud storage blob backup. |
| **Hosting Platform** | Vercel Serverless Functions | Production edge deployment with GitHub auto-deploy integration. |

---

## Getting Started Locally

### 1. Installation
```bash
git clone https://github.com/RamSujith2006/FA.git
cd FA
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### 2. Accessing the Website
- **Public Site**: `http://127.0.0.1:5000`
- **Admin Dashboard**: `http://127.0.0.1:5000/admin`
  - **Username**: `admin`
  - **Password**: `faevents2026`
