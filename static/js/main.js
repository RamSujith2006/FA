document.addEventListener("DOMContentLoaded", () => {
  /* ---------- Clear Browser & Service Worker Cache ---------- */
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      for (let reg of registrations) reg.unregister();
    }).catch(() => {});
  }
  if ("caches" in window) {
    caches.keys().then((names) => {
      for (let name of names) caches.delete(name);
    }).catch(() => {});
  }

  /* ---------- mobile nav ---------- */
  const navToggle = document.querySelector(".nav-toggle");
  if (navToggle) {
    navToggle.addEventListener("click", () => {
      document.body.classList.toggle("nav-open");
    });
    document.querySelectorAll(".nav-links a").forEach((link) => {
      link.addEventListener("click", () => document.body.classList.remove("nav-open"));
    });
  }

  /* ---------- gallery category filter ---------- */
  const tabs = document.querySelectorAll(".gallery-tabs button");
  const items = document.querySelectorAll("[data-category]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const cat = tab.dataset.filter;
      items.forEach((item) => {
        const show = cat === "all" || item.dataset.category === cat;
        item.style.display = show ? "" : "none";
      });
    });
  });

  /* ---------- Fullscreen Photo Gallery Lightbox Viewer ---------- */
  function initPhotoLightbox() {
    const lightbox = document.getElementById("photo-lightbox");
    if (!lightbox) return;

    const overlay = document.getElementById("lightbox-overlay");
    const closeBtn = document.getElementById("lightbox-close");
    const prevBtn = document.getElementById("lightbox-prev");
    const nextBtn = document.getElementById("lightbox-next");
    const mainImg = document.getElementById("lightbox-main-img");
    const titleEl = document.getElementById("lightbox-title");
    const counterEl = document.getElementById("lightbox-counter");

    let currentIndex = 0;
    let activeList = [];

    function getVisiblePhotos() {
      const figures = [...document.querySelectorAll(".gallery-item")].filter((fig) => {
        return fig.style.display !== "none" && window.getComputedStyle(fig).display !== "none";
      });
      return figures.map((fig) => {
        const img = fig.querySelector("img");
        const cap = fig.querySelector(".cap")?.textContent?.trim() || img?.getAttribute("alt") || "FA Events Decoration";
        return {
          src: img ? (img.currentSrc || img.src) : "",
          caption: cap,
          element: fig
        };
      }).filter((item) => !!item.src);
    }

    function openAt(index) {
      activeList = getVisiblePhotos();
      if (!activeList.length) return;
      if (index < 0) index = 0;
      if (index >= activeList.length) index = activeList.length - 1;
      currentIndex = index;

      showSlide(0);
      lightbox.style.display = "flex";
      void lightbox.offsetWidth;
      lightbox.classList.add("is-open");
      document.body.classList.add("lightbox-open");
      window.addEventListener("keydown", onKeydown);
    }

    function close() {
      lightbox.classList.remove("is-open");
      document.body.classList.remove("lightbox-open");
      window.removeEventListener("keydown", onKeydown);
      setTimeout(() => {
        if (!lightbox.classList.contains("is-open")) {
          lightbox.style.display = "none";
          mainImg.src = "";
        }
      }, 260);
    }

    function showSlide(dir = 0) {
      if (!activeList[currentIndex]) return;
      const cur = activeList[currentIndex];

      mainImg.style.opacity = "0";
      mainImg.style.transform = dir > 0 ? "scale(0.95) translateX(24px)" : dir < 0 ? "scale(0.95) translateX(-24px)" : "scale(0.95)";

      const preload = new Image();
      preload.src = cur.src;
      const applyImage = () => {
        mainImg.src = cur.src;
        mainImg.alt = cur.caption;
        if (titleEl) titleEl.textContent = cur.caption;
        if (counterEl) counterEl.textContent = `${currentIndex + 1} / ${activeList.length}`;
        requestAnimationFrame(() => {
          mainImg.style.opacity = "1";
          mainImg.style.transform = "scale(1) translateX(0)";
        });
      };
      preload.onload = applyImage;
      preload.onerror = applyImage;

      if (activeList.length <= 1) {
        if (prevBtn) prevBtn.style.display = "none";
        if (nextBtn) nextBtn.style.display = "none";
      } else {
        if (prevBtn) prevBtn.style.display = "flex";
        if (nextBtn) nextBtn.style.display = "flex";
      }
    }

    function next() {
      if (activeList.length <= 1) return;
      currentIndex = (currentIndex + 1) % activeList.length;
      showSlide(1);
    }

    function prev() {
      if (activeList.length <= 1) return;
      currentIndex = (currentIndex - 1 + activeList.length) % activeList.length;
      showSlide(-1);
    }

    function onKeydown(e) {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight" || e.key === "ArrowDown") next();
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") prev();
    }

    // Bind gallery items
    document.querySelectorAll(".gallery-item").forEach((fig) => {
      fig.style.cursor = "pointer";
      const clickHandler = (e) => {
        e.preventDefault();
        const currentItems = getVisiblePhotos();
        const clickedImg = fig.querySelector("img");
        const clickedSrc = clickedImg ? (clickedImg.currentSrc || clickedImg.src) : "";
        const foundIdx = currentItems.findIndex((item) => item.src === clickedSrc);
        openAt(foundIdx !== -1 ? foundIdx : 0);
      };
      fig.addEventListener("click", clickHandler);
      fig.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          clickHandler(e);
        }
      });
    });

    // Also bind review photos if present
    document.querySelectorAll(".review-photo-item").forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        const img = item.querySelector("img") || item;
        const src = item.getAttribute("href") || img.getAttribute("src");
        if (src) {
          activeList = [{ src, caption: "Customer Review Decor Photo" }];
          currentIndex = 0;
          showSlide(0);
          lightbox.style.display = "flex";
          void lightbox.offsetWidth;
          lightbox.classList.add("is-open");
          document.body.classList.add("lightbox-open");
          window.addEventListener("keydown", onKeydown);
        }
      });
    });

    if (closeBtn) closeBtn.addEventListener("click", close);
    if (overlay) overlay.addEventListener("click", close);
    if (nextBtn) nextBtn.addEventListener("click", (e) => { e.stopPropagation(); next(); });
    if (prevBtn) prevBtn.addEventListener("click", (e) => { e.stopPropagation(); prev(); });

    // Touch Swipe Detection for mobile screens
    let startX = 0;
    let startY = 0;
    lightbox.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    }, { passive: true });

    lightbox.addEventListener("touchend", (e) => {
      if (e.changedTouches.length === 1) {
        const diffX = e.changedTouches[0].clientX - startX;
        const diffY = e.changedTouches[0].clientY - startY;
        const absX = Math.abs(diffX);
        const absY = Math.abs(diffY);
        if (absX > 40 && absX > absY * 1.5) {
          if (diffX < 0) next();
          else prev();
        } else if (diffY > 80 && absY > absX * 1.5) {
          close();
        }
      }
    }, { passive: true });
  }

  initPhotoLightbox();

  /* ---------- star rating input ---------- */
  const starWrap = document.querySelector(".star-input");
  if (starWrap) {
    const buttons = [...starWrap.querySelectorAll("button")];
    const hiddenInput = document.getElementById("stars-value");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const val = Number(btn.dataset.star);
        hiddenInput.value = val;
        buttons.forEach((b) => b.classList.toggle("selected", Number(b.dataset.star) <= val));
      });
    });
  }

  /* ---------- AJAX: enquiry form ---------- */
  const enquiryForm = document.getElementById("enquiry-form");
  if (enquiryForm) {
    enquiryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msgBox = document.getElementById("enquiry-msg");
      const submitBtn = enquiryForm.querySelector("button[type=submit]");
      submitBtn.disabled = true;
      msgBox.textContent = "";
      msgBox.className = "form-msg";
      try {
        const res = await fetch(enquiryForm.action, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json"
          },
          body: new FormData(enquiryForm),
        });
        const data = await res.json();
        if (data.ok) {
          msgBox.textContent = data.message || "Thank you! We've received your enquiry and will contact you shortly.";
          msgBox.classList.add("ok");
          enquiryForm.reset();
        } else {
          msgBox.textContent = data.error || "Something went wrong. Please try again.";
          msgBox.classList.add("error");
        }
      } catch (err) {
        msgBox.textContent = "Network error — please try again or WhatsApp us directly.";
        msgBox.classList.add("error");
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  /* ---------- AJAX: rating form ---------- */
  const ratingForm = document.getElementById("rating-form");
  if (ratingForm) {
    ratingForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msgBox = document.getElementById("rating-msg");
      const submitBtn = ratingForm.querySelector("button[type=submit]");
      submitBtn.disabled = true;
      msgBox.textContent = "";
      msgBox.className = "form-msg";
      try {
        const res = await fetch(ratingForm.action, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json"
          },
          body: new FormData(ratingForm),
        });
        const data = await res.json();
        if (data.ok) {
          msgBox.textContent = data.message || "Thanks for your review!";
          msgBox.classList.add("ok");
          ratingForm.reset();
          document.querySelectorAll(".star-input button").forEach((b) => b.classList.remove("selected"));
        } else {
          msgBox.textContent = data.error || "Please add your name and a star rating.";
          msgBox.classList.add("error");
        }
      } catch (err) {
        msgBox.textContent = "Network error — please try again.";
        msgBox.classList.add("error");
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  /* ---------- Global Floating Yellow & Gold Particle Orbs Effect ---------- */
  const canvas = document.getElementById("particles-canvas");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    let width, height;
    let particles = [];

    function resize() {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    }

    window.addEventListener("resize", resize);
    resize();

    const colors = ["#ffd700", "#ffdf00", "#e6c875", "#d4af37", "#fff5cc", "#ffffff", "#ffc107"];

    class Particle {
      constructor() {
        this.reset(true);
      }

      reset(initial = false) {
        this.x = Math.random() * width;
        this.y = initial ? Math.random() * height : height + Math.random() * 30;
        this.size = Math.random() * 3.5 + 1.0;
        this.speedY = Math.random() * 0.45 + 0.18;
        this.speedX = (Math.random() - 0.5) * 0.3;
        this.maxOpacity = Math.random() * 0.85 + 0.25;
        this.opacity = initial ? Math.random() * this.maxOpacity : 0;
        this.fadeIn = true;
        this.color = colors[Math.floor(Math.random() * colors.length)];
        this.twinkleSpeed = Math.random() * 0.012 + 0.004;
      }

      update() {
        this.y -= this.speedY;
        this.x += this.speedX + Math.sin(this.y * 0.008) * 0.2;

        if (this.fadeIn) {
          this.opacity += this.twinkleSpeed;
          if (this.opacity >= this.maxOpacity) {
            this.fadeIn = false;
          }
        } else {
          this.opacity -= this.twinkleSpeed * 0.4;
        }

        if (this.y < -30 || this.opacity <= 0) {
          this.reset(false);
        }
      }

      draw() {
        if (this.opacity <= 0) return;
        ctx.save();
        ctx.globalAlpha = Math.max(0, this.opacity);
        ctx.shadowBlur = this.size * 8;
        ctx.shadowColor = "#ffd700";
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }

    const particleCount = Math.min(Math.floor((width * height) / 7000), 130);
    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }

    function animate() {
      ctx.clearRect(0, 0, width, height);
      particles.forEach((p) => {
        p.update();
        p.draw();
      });
      requestAnimationFrame(animate);
    }
    animate();
  }
});

/* =========================================================================
   Firebase Cloud Storage Manager Interactive Frontend Logic
   ========================================================================= */
let currentCloudFolder = "all";
let currentCloudQuery = "";
let currentCloudView = "grid";
let cloudFilesData = [];
let activeModalFile = null;

document.addEventListener("DOMContentLoaded", () => {
  const csGrid = document.getElementById("cs-files-grid");
  if (csGrid) {
    initCloudStorageConsole();
  }
});

function initCloudStorageConsole() {
  loadCloudStorageFiles();
  setupCloudDropzone();
}

function filterCloudFolder(folder, btn) {
  currentCloudFolder = folder;
  document.querySelectorAll(".cs-folder-tab").forEach(t => t.classList.remove("active"));
  if (btn) btn.classList.add("active");
  loadCloudStorageFiles();
}

function searchCloudFiles(val) {
  currentCloudQuery = val.trim();
  loadCloudStorageFiles();
}

function setCloudView(mode) {
  currentCloudView = mode;
  const gridBtn = document.getElementById("cs-view-grid-btn");
  const listBtn = document.getElementById("cs-view-list-btn");
  const container = document.getElementById("cs-files-grid");

  if (mode === "grid") {
    gridBtn?.classList.add("active");
    listBtn?.classList.remove("active");
    container.className = "cs-files-grid grid-mode";
  } else {
    listBtn?.classList.add("active");
    gridBtn?.classList.remove("active");
    container.className = "cs-files-grid list-mode";
  }
}

async function loadCloudStorageFiles() {
  const container = document.getElementById("cs-files-grid");
  if (!container) return;

  container.innerHTML = `<div class="cs-loading-spinner">⚡ Loading Cloud Storage files...</div>`;

  try {
    const url = `/admin/api/cloud-storage/files?folder=${encodeURIComponent(currentCloudFolder)}&q=${encodeURIComponent(currentCloudQuery)}&_t=${Date.now()}`;
    const res = await fetch(url, { cache: "no-store", headers: { "Cache-Control": "no-cache" } });
    const data = await res.json();
    cloudFilesData = data.files || [];
    renderCloudFiles(cloudFilesData);
  } catch (err) {
    container.innerHTML = `<div class="cs-loading-spinner" style="color:#f28b82;">⚠️ Failed to load cloud files. Reload page.</div>`;
  }
}

function renderCloudFiles(files) {
  const container = document.getElementById("cs-files-grid");
  if (!container) return;

  if (files.length === 0) {
    container.innerHTML = `<div class="cs-loading-spinner">No storage files found. Drag & drop files above to upload!</div>`;
    return;
  }

  let html = "";
  files.forEach(f => {
    const isVid = f.type === "video";
    const isEmbed = f.type === "video_embed";
    const displayUrl = f.display_url || f.local_url || "#";
    const cloudBadge = f.is_cloud_synced ? `<span class="cs-file-badge-cloud">☁️ Cloud</span>` : `<span class="cs-file-badge-cloud" style="background:#555;">💾 Local</span>`;
    const typeBadge = isVid || isEmbed ? `🎥 Video` : `📸 Photo`;

    let mediaPreview = "";
    if (isVid) {
      mediaPreview = `<video src="${displayUrl}" muted preload="metadata"></video>`;
    } else if (isEmbed) {
      mediaPreview = `<div style="padding:10px; font-size:0.75rem; text-align:center; color:var(--gold);">Embedded Link</div>`;
    } else {
      mediaPreview = `<img src="${displayUrl}" alt="${escapeHtml(f.caption || f.filename)}" loading="lazy">`;
    }

    html += `
      <div class="cs-file-card" data-id="${f.id}">
        <div class="cs-file-media-wrap" onclick="openCloudModal('${f.type}', ${f.id})">
          ${mediaPreview}
          <span class="cs-file-badge-type">${typeBadge}</span>
          ${cloudBadge}
        </div>
        <div class="cs-file-body">
          <div class="cs-file-name" title="${escapeHtml(f.filename)}">${escapeHtml(f.caption || f.filename)}</div>
          <div class="cs-file-meta">
            <span>${f.size_formatted}</span>
            <span>${f.category ? escapeHtml(f.category) : f.folder}</span>
          </div>
          <div class="cs-file-actions">
            <button class="mini-btn gold" style="flex:1;" onclick="openCloudModal('${f.type}', ${f.id})">Inspect</button>
            <button class="mini-btn" title="Copy URL" onclick="copyTextToClipboard('${escapeHtml(displayUrl)}')">📋</button>
            <button class="mini-btn danger" title="Delete" onclick="deleteCloudFile('${f.folder}', '${escapeHtml(f.filename)}', ${f.id})">🗑️</button>
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function setupCloudDropzone() {
  const dropzone = document.getElementById("cs-dropzone");
  const fileInput = document.getElementById("cs-file-input");
  if (!dropzone || !fileInput) return;

  ["dragenter", "dragover"].forEach(evt => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(evt => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      uploadFilesToCloud(files);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      uploadFilesToCloud(fileInput.files);
    }
  });
}

function triggerDirectUpload() {
  const fileInput = document.getElementById("cs-file-input");
  if (fileInput && fileInput.files && fileInput.files.length > 0) {
    uploadFilesToCloud(fileInput.files);
  } else {
    fileInput.click();
  }
}

async function uploadFilesToCloud(files) {
  const progressBox = document.getElementById("cs-upload-progress-container");
  const progressBar = document.getElementById("cs-upload-bar");
  const percentText = document.getElementById("cs-upload-percent");
  const statusText = document.getElementById("cs-upload-status-text");

  const caption = document.getElementById("cs-caption-input")?.value || "";
  const category = document.getElementById("cs-category-input")?.value || "";

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }
  formData.append("caption", caption);
  formData.append("category", category);
  formData.append("folder", currentCloudFolder);

  if (progressBox) progressBox.style.display = "block";
  if (statusText) statusText.textContent = `Uploading ${files.length} file(s) to Firebase Storage...`;
  if (progressBar) progressBar.style.width = "40%";
  if (percentText) percentText.textContent = "40%";

  try {
    const res = await fetch("/admin/api/cloud-storage/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.success) {
      if (progressBar) progressBar.style.width = "100%";
      if (percentText) percentText.textContent = "100%";
      if (statusText) statusText.textContent = `✅ Successfully uploaded ${data.count} file(s) to Cloud Storage!`;

      setTimeout(() => {
        if (progressBox) progressBox.style.display = "none";
        loadCloudStorageFiles();
      }, 1200);
    } else {
      if (statusText) statusText.textContent = `❌ Upload failed: ${data.error || "Unknown error"}`;
    }
  } catch (err) {
    if (statusText) statusText.textContent = `❌ Upload error: ${err.message}`;
  }
}

async function syncCloudStorage() {
  const btn = document.getElementById("cs-sync-btn");
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/admin/api/cloud-storage/sync", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      alert(`🎉 Firebase Storage Sync Complete!\nSynced: ${data.total_synced} files (${data.synced_photos} photos, ${data.synced_videos} videos).`);
      loadCloudStorageFiles();
    } else {
      alert(`⚠️ Sync notice: ${data.error || "Sync completed"}`);
    }
  } catch (err) {
    alert("Network error while syncing to Firebase Storage.");
  } finally {
    if (btn) btn.disabled = false;
  }
}

function openCloudModal(type, fileId) {
  const file = cloudFilesData.find(f => f.id === fileId && (f.type === type || f.folder === type || folderMatches(f, type)));
  if (!file) return;

  activeModalFile = file;

  const modal = document.getElementById("cs-media-modal");
  const previewBox = document.getElementById("cs-modal-preview-box");
  const title = document.getElementById("cs-modal-title");
  const filename = document.getElementById("cs-modal-filename");
  const folder = document.getElementById("cs-modal-folder");
  const size = document.getElementById("cs-modal-size");
  const mime = document.getElementById("cs-modal-type");
  const created = document.getElementById("cs-modal-created");
  const badge = document.getElementById("cs-modal-status-badge");
  const urlInput = document.getElementById("cs-modal-url-input");
  const embedInput = document.getElementById("cs-modal-embed-input");
  const downloadBtn = document.getElementById("cs-modal-download-btn");

  const displayUrl = file.display_url || file.cloud_url || file.local_url || "";

  if (file.type === "photo") {
    previewBox.innerHTML = `<img src="${displayUrl}" alt="${escapeHtml(file.caption || file.filename)}">`;
    embedInput.value = `<img src="${displayUrl}" alt="${escapeHtml(file.caption || 'Photo')}">`;
  } else if (file.type === "video") {
    previewBox.innerHTML = `<video src="${displayUrl}" controls autoplay style="width:100%; max-height:360px;"></video>`;
    embedInput.value = `<video src="${displayUrl}" controls></video>`;
  } else {
    previewBox.innerHTML = `<iframe src="${file.embed_url}" style="width:100%; height:260px; border:none;"></iframe>`;
    embedInput.value = `<iframe src="${file.embed_url}"></iframe>`;
  }

  title.textContent = file.caption || file.filename;
  filename.textContent = file.filename;
  folder.textContent = `/${file.folder}/`;
  size.textContent = file.size_formatted;
  mime.textContent = file.mime_type;
  created.textContent = file.created_at;
  badge.textContent = file.is_cloud_synced ? "☁️ Firebase Cloud Live" : "💾 Local Storage";
  badge.className = file.is_cloud_synced ? "cs-status-tag online" : "cs-status-tag offline";

  urlInput.value = displayUrl;
  downloadBtn.href = displayUrl;

  modal.style.display = "flex";
}

function folderMatches(file, targetType) {
  if (targetType === "photo" && file.folder === "photos") return true;
  if (targetType === "video" && file.folder === "videos") return true;
  return false;
}

function closeCloudModal() {
  const modal = document.getElementById("cs-media-modal");
  const previewBox = document.getElementById("cs-modal-preview-box");
  if (previewBox) previewBox.innerHTML = "";
  if (modal) modal.style.display = "none";
  activeModalFile = null;
}

function copyModalUrl() {
  const urlInput = document.getElementById("cs-modal-url-input");
  if (urlInput && urlInput.value) {
    copyTextToClipboard(urlInput.value);
  }
}

function copyModalEmbed() {
  const embedInput = document.getElementById("cs-modal-embed-input");
  if (embedInput && embedInput.value) {
    copyTextToClipboard(embedInput.value);
  }
}

function copyTextToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert("📋 Copied link to clipboard!");
  }).catch(() => {
    prompt("Copy text:", text);
  });
}

async function deleteCloudFile(folder, filename, id) {
  if (!confirm(`Are you sure you want to delete '${filename}' from Cloud Storage?`)) return;

  try {
    const res = await fetch("/admin/api/cloud-storage/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder, filename, id })
    });
    const data = await res.json();
    if (data.success) {
      loadCloudStorageFiles();
    } else {
      alert("Failed to delete file from Cloud Storage.");
    }
  } catch (err) {
    alert("Network error while deleting file.");
  }
}

async function deleteModalFile() {
  if (!activeModalFile) return;
  await deleteCloudFile(activeModalFile.folder, activeModalFile.filename, activeModalFile.id);
  closeCloudModal();
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* Direct Media Upload to Cloudinary for Photos & Videos (Batch & Multi-file Support) */
document.addEventListener("DOMContentLoaded", () => {
  setupDirectMediaUpload("video-upload-form", "video-file", "video-cloud-url", "video-upload-progress", "video-upload-percent", "video-submit-btn", "videos");
  setupDirectMediaUpload("photo-upload-form", "photo-file", "photo-cloud-url", "photo-upload-progress", "photo-upload-percent", "photo-submit-btn", "photos");

  const photoInput = document.getElementById("photo-file");
  if (photoInput) {
    photoInput.addEventListener("change", () => {
      renderMediaPreviews("photo-file", "photo-preview-box", "photo-preview-grid", "photo-preview-count");
    });
  }

  const videoInput = document.getElementById("video-file");
  if (videoInput) {
    videoInput.addEventListener("change", () => {
      renderMediaPreviews("video-file", "video-preview-box", "video-preview-grid", "video-preview-count");
    });
  }
});

function renderMediaPreviews(inputId, boxId, gridId, countId) {
  const fileInput = document.getElementById(inputId);
  const box = document.getElementById(boxId);
  const grid = document.getElementById(gridId);
  const countText = document.getElementById(countId);

  if (!fileInput || !box || !grid) return;
  const files = fileInput.files;

  if (!files || files.length === 0) {
    box.style.display = "none";
    grid.innerHTML = "";
    if (countText) countText.textContent = "0 selected";
    return;
  }

  const isVideo = (fileInput.accept && fileInput.accept.includes("video")) || (fileInput.name && fileInput.name.includes("video"));
  const noun = isVideo ? "video" : "photo";
  if (countText) {
    countText.textContent = `${files.length} ${noun}${files.length > 1 ? "s" : ""} selected`;
  }

  grid.innerHTML = "";
  box.style.display = "block";

  Array.from(files).forEach((file, idx) => {
    const card = document.createElement("div");
    card.className = "preview-card";

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "preview-remove-btn";
    removeBtn.innerHTML = "&times;";
    removeBtn.title = "Remove this file";
    removeBtn.onclick = (e) => {
      e.stopPropagation();
      removeFileFromInput(inputId, idx, boxId, gridId, countId);
    };

    const mediaHolder = document.createElement("div");
    mediaHolder.className = "preview-thumb-wrap";

    if (file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.alt = file.name;
      img.onload = () => URL.revokeObjectURL(img.src);
      mediaHolder.appendChild(img);
    } else if (file.type.startsWith("video/")) {
      const video = document.createElement("video");
      video.src = URL.createObjectURL(file);
      video.muted = true;
      video.playsInline = true;
      video.preload = "metadata";
      mediaHolder.appendChild(video);
    } else {
      mediaHolder.innerHTML = `<div class="preview-generic-icon">📁</div>`;
    }

    const info = document.createElement("div");
    info.className = "preview-info";
    const sizeKb = (file.size / 1024).toFixed(0);
    const sizeStr = file.size > 1048576 ? `${(file.size / 1048576).toFixed(1)} MB` : `${sizeKb} KB`;
    info.innerHTML = `<span class="preview-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span><span class="preview-size">${sizeStr}</span>`;

    card.appendChild(removeBtn);
    card.appendChild(mediaHolder);
    card.appendChild(info);
    grid.appendChild(card);
  });
}

function removeFileFromInput(inputId, indexToRemove, boxId, gridId, countId) {
  const fileInput = document.getElementById(inputId);
  if (!fileInput || !fileInput.files) return;

  try {
    const dt = new DataTransfer();
    for (let i = 0; i < fileInput.files.length; i++) {
      if (i !== indexToRemove) {
        dt.items.add(fileInput.files[i]);
      }
    }
    fileInput.files = dt.files;
  } catch (err) {
    console.warn("DataTransfer not supported:", err);
  }
  renderMediaPreviews(inputId, boxId, gridId, countId);
}

function clearSelectedMedia(inputId, boxId, gridId, countId) {
  const fileInput = document.getElementById(inputId);
  if (fileInput) fileInput.value = "";
  renderMediaPreviews(inputId, boxId, gridId, countId);
}

function setupDirectMediaUpload(formId, fileInputId, cloudUrlInputId, progressBoxId, percentTextId, submitBtnId, folder) {
  const form = document.getElementById(formId);
  const fileInput = document.getElementById(fileInputId);
  const cloudUrlInput = document.getElementById(cloudUrlInputId);
  const cloudUrlsInput = document.getElementById(folder === "videos" ? "video-cloud-urls" : "photo-cloud-urls");
  const progressBox = document.getElementById(progressBoxId);
  const percentText = document.getElementById(percentTextId);
  const progressBarFill = document.getElementById(folder === "videos" ? "video-progress-bar-fill" : "photo-progress-bar-fill");
  const submitBtn = document.getElementById(submitBtnId);

  if (!form || !fileInput) return;

  function resetUploadUI() {
    if (submitBtn) submitBtn.disabled = false;
    if (progressBox) progressBox.style.display = "none";
    if (percentText) percentText.textContent = "0%";
    if (progressBarFill) progressBarFill.style.width = "0%";
  }

  form.addEventListener("submit", async (e) => {
    // If no file is attached, let form submit naturally (e.g. for video embed link)
    if (!fileInput.files || fileInput.files.length === 0) {
      return;
    }

    // If cloud URLs are already populated, let form submit
    if ((cloudUrlsInput && cloudUrlsInput.value) || (cloudUrlInput && cloudUrlInput.value)) {
      return;
    }

    e.preventDefault();

    const files = Array.from(fileInput.files);
    const totalFiles = files.length;
    const isVideo = folder === "videos";
    const itemNoun = isVideo ? "video" : "photo";

    if (submitBtn) submitBtn.disabled = true;
    if (progressBox) progressBox.style.display = "block";
    if (percentText) percentText.textContent = `0% (Preparing ${totalFiles} ${itemNoun}${totalFiles > 1 ? "s" : ""} for cloud upload...)`;
    if (progressBarFill) progressBarFill.style.width = "0%";

    const uploadedUrls = [];

    try {
      for (let i = 0; i < totalFiles; i++) {
        const file = files[i];

        // Step 1: Request signature from backend
        const signRes = await fetch(`/admin/api/cloudinary-sign?folder=${folder}`);
        if (!signRes.ok) {
          throw new Error("Could not authenticate with Cloud Storage server.");
        }

        const signData = await signRes.json();
        if (!signData.signature || !signData.cloud_name) {
          throw new Error(signData.error || "Could not retrieve upload credentials");
        }

        // Step 2: Prepare FormData for direct Cloudinary upload (file MUST be appended last!)
        const formData = new FormData();
        formData.append("api_key", signData.api_key);
        formData.append("timestamp", String(signData.timestamp));
        formData.append("folder", signData.folder);
        formData.append("signature", signData.signature);
        formData.append("file", file);

        const resourceType = signData.resource_type || (isVideo ? "video" : "image");
        const uploadUrl = `https://api.cloudinary.com/v1_1/${signData.cloud_name}/${resourceType}/upload`;

        const secureUrl = await new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.open("POST", uploadUrl, true);

          xhr.upload.onprogress = (evt) => {
            if (evt.lengthComputable) {
              const filePercent = Math.round((evt.loaded / evt.total) * 100);
              const overallPercent = Math.round(((i * 100) + filePercent) / totalFiles);
              if (percentText) {
                percentText.textContent = `Uploading ${itemNoun} ${i + 1} of ${totalFiles} (${filePercent}%) — Overall: ${overallPercent}%`;
              }
              if (progressBarFill) {
                progressBarFill.style.width = `${overallPercent}%`;
              }
            }
          };

          xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const resData = JSON.parse(xhr.responseText);
                const url = resData.secure_url || resData.url;
                if (url) {
                  resolve(url);
                } else {
                  reject(new Error("No URL returned from Cloud Storage."));
                }
              } catch (err) {
                reject(err);
              }
            } else {
              let errMessage = `Upload failed with status ${xhr.status}`;
              try {
                const errData = JSON.parse(xhr.responseText);
                if (errData.error && errData.error.message) {
                  errMessage = errData.error.message;
                }
              } catch (_) {}
              reject(new Error(errMessage));
            }
          };

          xhr.onerror = function() {
            reject(new Error("Network error while uploading to Cloud Storage. Please check your connection."));
          };

          xhr.send(formData);
        });

        uploadedUrls.push(secureUrl);
      }

      // Step 3: Save uploaded URLs to database via fetch
      if (percentText) percentText.textContent = `100% (Saving ${uploadedUrls.length} ${itemNoun}${uploadedUrls.length > 1 ? "s" : ""} to gallery...)`;
      if (progressBarFill) progressBarFill.style.width = "100%";

      const saveEndpoint = folder === "videos" ? "/admin/video/upload" : "/admin/photo/upload";
      const savePayload = {
        cloud_urls: uploadedUrls,
        caption: document.getElementById(folder === "videos" ? "video-caption" : "photo-caption")?.value || "",
        category: document.getElementById(folder === "videos" ? "video-category" : "photo-category")?.value || ""
      };

      try {
        const saveRes = await fetch(saveEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
          },
          body: JSON.stringify(savePayload)
        });

        if (saveRes.ok) {
          if (percentText) percentText.textContent = `✅ Successfully saved to gallery! Refreshing...`;
          setTimeout(() => {
            window.location.hash = folder === "videos" ? "#videos" : "#gallery";
            window.location.reload();
          }, 600);
          return;
        }
      } catch (saveErr) {
        console.warn("Fetch save failed, falling back to form submit:", saveErr);
      }

      // Fallback: populate hidden inputs and submit form
      if (cloudUrlsInput) cloudUrlsInput.value = JSON.stringify(uploadedUrls);
      if (cloudUrlInput && uploadedUrls.length > 0) cloudUrlInput.value = uploadedUrls[0];
      fileInput.value = "";
      form.submit();

    } catch (err) {
      alert(`⚠️ Cloud Upload Error: ${err.message}`);
      resetUploadUI();
    }
  });
}


