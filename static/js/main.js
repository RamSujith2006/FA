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
          body: new FormData(enquiryForm),
        });
        const data = await res.json();
        if (data.ok) {
          msgBox.textContent = "Thank you! We've received your enquiry and will contact you shortly.";
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
});
