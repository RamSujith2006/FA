document.addEventListener("DOMContentLoaded", () => {
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
    const url = `/admin/api/cloud-storage/files?folder=${encodeURIComponent(currentCloudFolder)}&q=${encodeURIComponent(currentCloudQuery)}`;
    const res = await fetch(url);
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

/* Direct Media Upload to Cloudinary for Videos (Bypasses Vercel 4.5MB Payload Limit) */
document.addEventListener("DOMContentLoaded", () => {
  setupDirectMediaUpload("video-upload-form", "video-file", "video-cloud-url", "video-upload-progress", "video-upload-percent", "video-submit-btn", "videos");
});

function setupDirectMediaUpload(formId, fileInputId, cloudUrlInputId, progressBoxId, percentTextId, submitBtnId, folder) {
  const form = document.getElementById(formId);
  const fileInput = document.getElementById(fileInputId);
  const cloudUrlInput = document.getElementById(cloudUrlInputId);
  const progressBox = document.getElementById(progressBoxId);
  const percentText = document.getElementById(percentTextId);
  const submitBtn = document.getElementById(submitBtnId);

  if (!form || !fileInput) return;

  function resetUploadUI() {
    if (submitBtn) submitBtn.disabled = false;
    if (progressBox) progressBox.style.display = "none";
    if (percentText) percentText.textContent = "0%";
  }

  form.addEventListener("submit", async (e) => {
    // If no file is attached, let form submit naturally (e.g. for video embed link)
    if (!fileInput.files || fileInput.files.length === 0) {
      return;
    }

    // If cloud_url is already populated, let form submit
    if (cloudUrlInput && cloudUrlInput.value) {
      return;
    }

    e.preventDefault();

    const file = fileInput.files[0];

    // Disable submit button & show progress box
    if (submitBtn) submitBtn.disabled = true;
    if (progressBox) progressBox.style.display = "block";
    if (percentText) percentText.textContent = "0% (Preparing video upload...)";

    try {
      // Step 1: Request signature from backend
      const signRes = await fetch(`/admin/api/cloudinary-sign?folder=${folder}`);
      if (!signRes.ok) {
        throw new Error("Could not authenticate with Cloud Storage server.");
      }

      const signData = await signRes.json();
      if (!signData.signature || !signData.cloud_name) {
        throw new Error(signData.error || "Could not retrieve upload credentials");
      }

      // Step 2: Prepare FormData for direct Cloudinary upload
      const formData = new FormData();
      formData.append("file", file);
      formData.append("api_key", signData.api_key);
      formData.append("timestamp", String(signData.timestamp));
      formData.append("folder", signData.folder);
      formData.append("signature", signData.signature);

      const resourceType = folder === "videos" ? "video" : "auto";
      const uploadUrl = `https://api.cloudinary.com/v1_1/${signData.cloud_name}/${resourceType}/upload`;

      // Use XMLHttpRequest to enable accurate upload percentage progress
      const xhr = new XMLHttpRequest();
      xhr.open("POST", uploadUrl, true);

      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable) {
          const percent = Math.round((evt.loaded / evt.total) * 100);
          if (percentText) percentText.textContent = `${percent}% (Uploading to Cloud Storage...)`;
        }
      };

      xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const resData = JSON.parse(xhr.responseText);
            const secureUrl = resData.secure_url || resData.url;

            if (secureUrl) {
              if (percentText) percentText.textContent = "100% (Saving video details...)";
              if (cloudUrlInput) cloudUrlInput.value = secureUrl;

              // Clear heavy binary file from input so Vercel payload stays tiny (<1KB)
              fileInput.value = "";

              // Submit form with text fields (cloud_url, caption, category)
              form.submit();
            } else {
              alert("Upload completed but failed to parse cloud storage URL.");
              resetUploadUI();
            }
          } catch (e) {
            alert("Error parsing upload response from Cloud Storage.");
            resetUploadUI();
          }
        } else {
          let errMessage = `Upload failed with status ${xhr.status}`;
          try {
            const errData = JSON.parse(xhr.responseText);
            if (errData.error && errData.error.message) {
              errMessage = errData.error.message;
            }
          } catch (_) {}
          alert(`Cloud Storage Upload Error: ${errMessage}`);
          resetUploadUI();
        }
      };

      xhr.onerror = function() {
        alert("Network error occurred while streaming video to Cloud Storage.");
        resetUploadUI();
      };

      xhr.send(formData);

    } catch (err) {
      console.error("Direct upload error:", err);
      alert(`Video Upload Error: ${err.message || "Failed to upload video to Cloud Storage"}`);
      resetUploadUI();
    }
  });
}


