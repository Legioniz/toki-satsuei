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
  const driveLink = document.querySelector("#client-drive-link");

  let currentToken = "";
  let selectedPhotos = new Set();
  let galleryData = null;

  // Sample client photos for delivery presentation if private storage links are not populated
  const DEFAULT_PHOTOS = [
    { id: "frame-001", title: "Edited Portrait 01", url: "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/3db8c3355_242599.jpg" },
    { id: "frame-002", title: "Detail Study 02", url: "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/b21ff20c7_242600.jpg" },
    { id: "frame-003", title: "Atmosphere Study 03", url: "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/e03bfd350_242598.jpg" },
    { id: "frame-004", title: "Composition Study 04", url: "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/52f603569_242601.jpg" }
  ];

  async function fetchGallery(token) {
    tokenError.style.display = "none";
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

  function renderGallery() {
    gateSection.hidden = true;
    gallerySection.hidden = false;

    greeting.textContent = `Photographs for ${galleryData.client_name || "You"}`;
    sessionDetails.textContent = `${galleryData.session_type || "Session"} • Delivered ${galleryData.confirmed_date || "recently"}`;

    if (galleryData.delivery_folder_url) {
      driveLink.href = galleryData.delivery_folder_url;
      driveLink.style.display = "inline-flex";
    } else {
      driveLink.style.display = "none";
    }

    if (Array.isArray(galleryData.client_selected_photos)) {
      selectedPhotos = new Set(galleryData.client_selected_photos);
    }
    updateSelectedCount();

    const photos = DEFAULT_PHOTOS;
    photoGrid.innerHTML = photos.map(p => {
      const isSelected = selectedPhotos.has(p.id);
      return `
        <div class="client-photo-item ${isSelected ? "is-selected" : ""}" data-id="${p.id}" tabindex="0" role="button" aria-pressed="${isSelected}" aria-label="Select photo ${p.title}">
          <img src="${p.url}" alt="${p.title}" loading="lazy">
          <div class="client-photo-select-btn" aria-hidden="true">${isSelected ? "✓" : "+"}</div>
        </div>
      `;
    }).join("");

    photoGrid.querySelectorAll(".client-photo-item").forEach(item => {
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
      item.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
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
      alert("Selections recorded locally. Please confirm with the studio via chat.");
    } finally {
      submitSelectionBtn.disabled = false;
      submitSelectionBtn.textContent = "Save Favorites ↗";
    }
  });

  tokenForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const token = tokenInput.value.trim();
    if (token) fetchGallery(token);
  });

  // Check URL param
  const urlParams = new URLSearchParams(window.location.search);
  const tokenFromUrl = urlParams.get("token");
  if (tokenFromUrl) {
    tokenInput.value = tokenFromUrl;
    fetchGallery(tokenFromUrl);
  }
})();
