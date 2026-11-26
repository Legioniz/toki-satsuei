(() => {
  "use strict";

  const SUPABASE_URL = "https://pjuwrngnrrvdiwqspkic.supabase.co";
  const PUBLISHABLE_KEY = "sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS";

  const gateSection = document.querySelector("#client-gate-section");
  const gallerySection = document.querySelector("#client-gallery-section");
  const tokenForm = document.querySelector("#client-token-form");
  const tokenInput = document.querySelector("#client-token-input");
  const tokenError = document.querySelector("#client-token-error");

  const greeting = document.querySelector("#client-greeting");
  const sessionDetails = document.querySelector("#client-session-details");
  const selectedCountDisplay = document.querySelector("#client-selected-count");
  const submitSelectionBtn = document.querySelector("#client-submit-selection-btn");
  const photoGrid = document.querySelector("#client-photo-grid");

  let currentToken = "";
  let selectedPhotos = new Set();
  let galleryData = null;

  const selectionSummary = document.querySelector(".client-selection-summary");


  async function fetchGallery(token) {
    tokenError.style.display = "none";
    currentToken = "";
    galleryData = null;
    try {
      const res = await fetch(SUPABASE_URL + "/rest/v1/rpc/toki_get_client_gallery", {
        method: "POST",
        headers: {
          "apikey": PUBLISHABLE_KEY,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ p_token: token })
      });

      if (!res.ok) {
        throw new Error("RPC error");
      }

      const data = await res.json();
      if (!data || data.ok !== true) {
        tokenError.textContent = data?.message || "Invalid or expired access key.";
        tokenError.style.display = "block";
        return false;
      }

      galleryData = data;
      currentToken = token;
      renderGallery();
      return true;
    } catch {
      tokenError.textContent = "Unable to verify access key with the studio server.";
      tokenError.style.display = "block";
      return false;
    }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[character]);
  }

  function renderGallery() {
    gateSection.hidden = true;
    gallerySection.hidden = false;

    greeting.textContent = `Photographs for ${galleryData.client_name || "You"}`;
    sessionDetails.textContent = `${galleryData.session_type || "Session"} • Delivered ${galleryData.confirmed_date || "recently"}`;

    const suppliedPhotos = Array.isArray(galleryData.photos) ? galleryData.photos : [];
    const photos = suppliedPhotos.map((photo) => {
      if (!photo || typeof photo.id !== "string" || typeof photo.title !== "string" || typeof photo.url !== "string") return null;
      try {
        const url = new URL(photo.url);
        if (url.protocol !== "https:") return null;
        return { id: photo.id, title: photo.title, url: url.href };
      } catch {
        return null;
      }
    }).filter(Boolean);

    if (!photos.length) {
      selectedPhotos.clear();
      if (selectionSummary) selectionSummary.hidden = true;
      photoGrid.innerHTML = `
        <div class="client-gallery-empty" role="status">
          <span class="client-gallery-empty__eyebrow">PRIVATE DELIVERY</span>
          <h2>Your files are shared through the studio's private delivery link.</h2>
          <p>This portal has verified your access key, but a private photo preview list has not been connected to this delivery yet. Contact the studio through your official booking conversation to request your photographs.</p>
        </div>
      `;
      return;
    }

    if (selectionSummary) selectionSummary.hidden = false;
    selectedPhotos = new Set(
      Array.isArray(galleryData.client_selected_photos)
        ? galleryData.client_selected_photos.filter((id) => typeof id === "string")
        : []
    );
    updateSelectedCount();

    photoGrid.innerHTML = photos.map((photo) => {
      const isSelected = selectedPhotos.has(photo.id);
      return `
        <div class="client-photo-item ${isSelected ? "is-selected" : ""}" data-id="${escapeHtml(photo.id)}" tabindex="0" role="button" aria-pressed="${isSelected}" aria-label="Select photo ${escapeHtml(photo.title)}">
          <img src="${escapeHtml(photo.url)}" alt="${escapeHtml(photo.title)}" loading="lazy" decoding="async">
          <div class="client-photo-select-btn" aria-hidden="true">${isSelected ? "✓" : "+"}</div>
        </div>
      `;
    }).join("");

    photoGrid.querySelectorAll(".client-photo-item").forEach((item) => {
      const toggle = () => {
        const id = item.dataset.id;
        if (selectedPhotos.has(id)) {
          selectedPhotos.delete(id);
          item.classList.remove("is-selected");
          item.setAttribute("aria-pressed", "false");
          item.querySelector(".client-photo-select-btn").textContent = "+";
        } else {
          selectedPhotos.add(id);
          item.classList.add("is-selected");
          item.setAttribute("aria-pressed", "true");
          item.querySelector(".client-photo-select-btn").textContent = "✓";
        }
        updateSelectedCount();
      };
      item.addEventListener("click", toggle);
      item.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          toggle();
        }
      });
    });
  }

  function updateSelectedCount() {
    selectedCountDisplay.textContent = `${selectedPhotos.size} photo${selectedPhotos.size === 1 ? "" : "s"}`;
  }

  submitSelectionBtn?.addEventListener("click", async () => {
    submitSelectionBtn.disabled = true;
    submitSelectionBtn.textContent = "Saving...";

    try {
      const res = await fetch(SUPABASE_URL + "/rest/v1/rpc/toki_submit_client_selection", {
        method: "POST",
        headers: {
          "apikey": PUBLISHABLE_KEY,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          p_token: currentToken,
          p_selections: Array.from(selectedPhotos)
        })
      });

      const data = await res.json();
      if (res.ok && data?.ok) {
        alert("Favorites saved successfully! The studio has been notified of your selections.");
      } else {
        alert(data?.message || "Failed to save selections. Please try again.");
      }
    } catch {
      alert("Could not reach the studio server. Your selections were not saved. Check your connection and try again.");
    } finally {
      submitSelectionBtn.disabled = false;
      submitSelectionBtn.textContent = "Save Favorites ↗";
    }
  });

  tokenForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const token = tokenInput.value.trim().toLowerCase();
    tokenInput.value = "";
    if (!/^toki-[0-9a-f]{64}$/.test(token)) {
      tokenError.textContent = "Enter the complete private delivery key provided by the studio.";
      tokenError.style.display = "block";
      return;
    }
    void fetchGallery(token);
  });

  // Access keys are entered into the password field, never placed in a URL.
})();
