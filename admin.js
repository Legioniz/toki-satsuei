(() => {
  "use strict";

  const SUPABASE_URL = "https://pjuwrngnrrvdiwqspkic.supabase.co";
  const PUBLISHABLE_KEY = "sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS";

  // Elements
  const authSection = document.querySelector("#admin-auth-section");
  const dashboardSection = document.querySelector("#admin-dashboard-section");
  const loginForm = document.querySelector("#admin-login-form");
  const emailInput = document.querySelector("#admin-email");
  const passwordInput = document.querySelector("#admin-password");
  const authError = document.querySelector("#admin-auth-error");
  const userNav = document.querySelector("#admin-user-nav");
  const userEmailDisplay = document.querySelector("#admin-user-email");
  const logoutBtn = document.querySelector("#admin-logout-btn");

  const searchInput = document.querySelector("#admin-search-input");
  const filterPills = document.querySelectorAll(".admin-pill");
  const bookingTbody = document.querySelector("#admin-booking-tbody");

  // Metrics
  const metricTotal = document.querySelector("#metric-total");
  const metricReview = document.querySelector("#metric-review");
  const metricConfirmed = document.querySelector("#metric-confirmed");
  const metricEditing = document.querySelector("#metric-editing");
  const metricDelivered = document.querySelector("#metric-delivered");

  // Modal
  const modal = document.querySelector("#admin-detail-modal");
  const modalCloseBtn = document.querySelector("#modal-close-btn");
  const modalCancelBtn = document.querySelector("#modal-cancel-btn");
  const modalForm = document.querySelector("#admin-booking-form");
  const modalBookingId = document.querySelector("#modal-booking-id");
  const modalBookingRef = document.querySelector("#modal-booking-ref");
  const modalClientName = document.querySelector("#modal-client-name");
  const modalContactInfo = document.querySelector("#modal-contact-info");
  const modalSessionType = document.querySelector("#modal-session-type");
  const modalRequestedDateTime = document.querySelector("#modal-requested-datetime");
  const modalParticipantsLocation = document.querySelector("#modal-participants-location");
  const modalClientNotes = document.querySelector("#modal-client-notes");
  const modalStatusSelect = document.querySelector("#modal-status-select");
  const modalConfirmedDate = document.querySelector("#modal-confirmed-date");
  const modalStartTime = document.querySelector("#modal-start-time");
  const modalEndTime = document.querySelector("#modal-end-time");
  const modalTotalPrice = document.querySelector("#modal-total-price");
  const modalReservationFee = document.querySelector("#modal-reservation-fee");
  const modalReservationPaid = document.querySelector("#modal-reservation-paid");
  const modalBalancePaid = document.querySelector("#modal-balance-paid");
  const modalDeliveryUrl = document.querySelector("#modal-delivery-url");
  const modalDeliveryToken = document.querySelector("#modal-delivery-token");
  const modalGenTokenBtn = document.querySelector("#modal-gen-token-btn");
  const modalCopyTokenBtn = document.querySelector("#modal-copy-token-btn");
  const modalAdminNotes = document.querySelector("#modal-admin-notes");

  let currentSession = null;
  let allBookings = [];
  let currentFilter = "all";
  let searchQuery = "";
  let adminIdleTimer = null;
  const ADMIN_IDLE_TIMEOUT_MS = 20 * 60 * 1000;

  // Helper: headers for authenticated requests
  function getAuthHeaders() {
    const token = currentSession?.access_token || "";
    return {
      "apikey": PUBLISHABLE_KEY,
      "Authorization": "Bearer " + token,
      "Content-Type": "application/json",
      "Prefer": "return=representation"
    };
  }

  // Auth: Check saved session
  function initSession() {
    try {
      const saved = sessionStorage.getItem("toki_admin_session");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed?.access_token && parsed?.expires_at > Date.now() / 1000) {
          currentSession = { access_token: parsed.access_token, expires_at: parsed.expires_at, user: { email: parsed.user?.email || "" } };
          sessionStorage.setItem("toki_admin_session", JSON.stringify(currentSession));
          showDashboard();
          return;
        }
      }
    } catch {
      sessionStorage.removeItem("toki_admin_session");
    }
    showAuth();
  }

  function showAuth() {
    if (adminIdleTimer) window.clearTimeout(adminIdleTimer);
    adminIdleTimer = null;
    currentSession = null;
    sessionStorage.removeItem("toki_admin_session");
    authSection.hidden = false;
    dashboardSection.hidden = true;
    userNav.hidden = true;
  }

  function scheduleAdminIdleLogout() {
    if (adminIdleTimer) window.clearTimeout(adminIdleTimer);
    if (currentSession?.access_token) adminIdleTimer = window.setTimeout(() => { void logoutAdminSession(); }, ADMIN_IDLE_TIMEOUT_MS);
  }

  async function logoutAdminSession() {
    const accessToken = currentSession?.access_token || "";
    showAuth();
    if (!accessToken) return;
    try {
      await fetch(SUPABASE_URL + "/auth/v1/logout", { method: "POST", headers: { "apikey": PUBLISHABLE_KEY, "Authorization": "Bearer " + accessToken } });
    } catch { /* Local credentials are cleared even if remote revocation is unavailable. */ }
  }

  ["pointerdown", "keydown", "touchstart"].forEach((eventName) => document.addEventListener(eventName, scheduleAdminIdleLogout, { passive: true }));

  function showDashboard() {
    scheduleAdminIdleLogout();
    authSection.hidden = true;
    dashboardSection.hidden = false;
    userNav.hidden = false;
    userEmailDisplay.textContent = currentSession?.user?.email || "Admin";
    loadBookings();
  }

  // Auth: Login
  loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    authError.style.display = "none";
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    try {
      const res = await fetch(SUPABASE_URL + "/auth/v1/token?grant_type=password", {
        method: "POST",
        headers: {
          "apikey": PUBLISHABLE_KEY,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
      });

      const data = await res.json();
      if (!res.ok) {
        authError.textContent = data.error_description || data.msg || "Authentication failed. Verify credentials.";
        authError.style.display = "block";
        return;
      }

      // Persist only the short-lived access token; never store the refresh token in browser storage.
      currentSession = { access_token: data.access_token, expires_at: data.expires_at, user: { email: data.user?.email || email } };
      sessionStorage.setItem("toki_admin_session", JSON.stringify(currentSession));
      showDashboard();
    } catch (err) {
      authError.textContent = "Unable to connect to authorization service.";
      authError.style.display = "block";
    }
  });

  logoutBtn?.addEventListener("click", () => { void logoutAdminSession(); });

  // Fetch Bookings
  async function loadBookings() {
    bookingTbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:28px;color:var(--admin-subtext);">Fetching booking inbox...</td></tr>`;
    try {
      const res = await fetch(SUPABASE_URL + "/rest/v1/toki_booking_requests?select=*&order=created_at.desc", {
        headers: getAuthHeaders()
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          showAuth();
          return;
        }
        throw new Error("Query failed");
      }

      allBookings = await res.json();
      renderDashboard();
    } catch (err) {
      bookingTbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:28px;color:#f1a1a6;">Failed to load bookings. Please check authorization policies.</td></tr>`;
    }
  }

  function renderDashboard() {
    updateMetrics();
    renderTable();
  }

  function updateMetrics() {
    metricTotal.textContent = String(allBookings.length);
    metricReview.textContent = String(allBookings.filter(b => b.status === "reviewing").length);
    metricConfirmed.textContent = String(allBookings.filter(b => b.status === "confirmed").length);
    metricEditing.textContent = String(allBookings.filter(b => b.delivery_status === "editing").length);
    metricDelivered.textContent = String(allBookings.filter(b => b.delivery_status === "delivered").length);
  }

  function formatSessionAddons(b) {
    const parts = [];
    const photos = Number(b.additional_photos || 0);
    const mins = Number(b.additional_time || 0);
    if (photos > 0) parts.push(`+${photos} photo${photos === 1 ? "" : "s"}`);
    if (mins > 0) parts.push(`+${mins} mins`);
    return parts.length ? ` (${parts.join(", ")})` : "";
  }

  function renderTable() {
    const filtered = allBookings.filter(b => {
      const matchesFilter = currentFilter === "all" || b.status === currentFilter;
      const q = searchQuery.toLowerCase();
      const matchesSearch = !q ||
        (b.name && b.name.toLowerCase().includes(q)) ||
        (b.reference_code && b.reference_code.toLowerCase().includes(q)) ||
        (b.contact_value && b.contact_value.toLowerCase().includes(q));
      return matchesFilter && matchesSearch;
    });

    if (!filtered.length) {
      bookingTbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--admin-subtext);">No booking records found matching current criteria.</td></tr>`;
      return;
    }

    bookingTbody.innerHTML = filtered.map(b => {
      const statusClass = "status-tag--" + (
        b.status === "new" ? "new" :
        b.status === "reviewing" ? "review" :
        b.status === "confirmed" ? "confirmed" : "cancelled"
      );
      const statusLabel = ({ new: "New", reviewing: "Under Review", confirmed: "Confirmed", declined: "Declined", cancelled: "Cancelled" })[b.status] || "New";
      const feeStatus = b.reservation_fee_paid ? "Fee Paid" : "Fee Due";
      const feeColor = b.reservation_fee_paid ? "#76d69e" : "#df6871";

      return `
        <tr data-id="${b.id}">
          <td><strong style="font-family:var(--c-mono, monospace);">${escapeHtml(b.reference_code || "—")}</strong></td>
          <td>
            <div style="font-weight:600;color:#f4f1ea;">${escapeHtml(b.name || "Anonymous")}</div>
            <div style="font-size:11px;color:var(--admin-subtext);font-family:var(--c-mono, monospace);">${escapeHtml(b.contact_method || "")}: ${escapeHtml(b.contact_value || "")}</div>
          </td>
          <td>
            <div style="color:#ede6dd;">${escapeHtml((b.session_type || "Session") + formatSessionAddons(b))}</div>
            <div style="font-size:12px;color:var(--admin-subtext);">${escapeHtml(b.confirmed_date || b.preferred_date || "—")} (${escapeHtml(b.preferred_time || "—")})</div>
          </td>
          <td><span class="status-tag ${statusClass}">${escapeHtml(statusLabel)}</span></td>
          <td>
            <div style="font-size:12px;color:${feeColor};">${feeStatus}</div>
            <div style="font-size:11px;color:var(--admin-subtext);font-family:var(--c-mono, monospace);">₱${Number(b.total_price || 0).toFixed(2)}</div>
          </td>
          <td>
            <button type="button" class="admin-btn admin-btn-secondary btn-manage-booking admin-action-btn" data-id="${b.id}" style="width:auto;min-height:32px;padding:0 12px;font-size:11px;">Manage ↗</button>
          </td>
        </tr>
      `;
    }).join("");

    bookingTbody.querySelectorAll(".btn-manage-booking").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.id;
        const booking = allBookings.find(b => String(b.id) === String(id));
        if (booking) openBookingModal(booking);
      });
    });
  }

  // Filter & Search Events
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      filterPills.forEach(p => p.classList.remove("is-active"));
      pill.classList.add("is-active");
      currentFilter = pill.dataset.status;
      renderTable();
    });
  });

  searchInput?.addEventListener("input", (e) => {
    searchQuery = e.target.value.trim();
    renderTable();
  });

  // Modal Open
  function openBookingModal(b) {
    modalBookingId.value = b.id;
    modalBookingRef.textContent = b.reference_code || "TOKI-";
    modalClientName.textContent = b.name || "Client";
    modalContactInfo.textContent = `${b.contact_method || "Contact"}: ${b.contact_value || "—"}`;
    modalSessionType.textContent = (b.session_type || "—") + formatSessionAddons(b);
    modalRequestedDateTime.textContent = `${b.preferred_date || "—"} at ${b.preferred_time || "—"}${b.alternate_date ? ` (Alt: ${b.alternate_date})` : ""}`;
    modalParticipantsLocation.textContent = `${b.participants || 1} participant(s) at ${b.location || "Quezon City"}`;
    modalClientNotes.textContent = b.notes || "No additional notes provided.";

    modalStatusSelect.value = b.status || "new";
    modalConfirmedDate.value = b.confirmed_date || "";
    modalStartTime.value = b.confirmed_start_time ? b.confirmed_start_time.slice(0, 8) : "";
    modalEndTime.value = b.confirmed_end_time ? b.confirmed_end_time.slice(0, 8) : "";

    modalTotalPrice.value = b.total_price ? Number(b.total_price).toFixed(2) : "";
    modalReservationFee.value = b.reservation_fee ? Number(b.reservation_fee).toFixed(2) : "";
    modalReservationPaid.checked = Boolean(b.reservation_fee_paid);
    modalBalancePaid.checked = Boolean(b.balance_paid);

    modalDeliveryUrl.value = b.delivery_folder_url || "";
    modalDeliveryToken.value = "";
    modalDeliveryToken.dataset.hasToken = String(Boolean(b.delivery_token_hash));
    modalDeliveryToken.dataset.currentStatus = b.delivery_status || "pending";
    modalDeliveryToken.placeholder = b.delivery_token_hash ? "Saved key cannot be viewed. Generate a new key to rotate it." : "Generate a new private key";
    modalAdminNotes.value = b.admin_notes || "";

    modal.hidden = false;
  }

  function closeBookingModal() {
    modalDeliveryToken.value = "";
    modal.hidden = true;
  }

  modalCloseBtn?.addEventListener("click", closeBookingModal);
  modalCancelBtn?.addEventListener("click", closeBookingModal);

  modalGenTokenBtn?.addEventListener("click", () => {
    if (!window.crypto || typeof window.crypto.getRandomValues !== "function") {
      modalDeliveryToken.value = "";
      window.alert("Secure token generation is unavailable in this browser. Use an updated browser over HTTPS.");
      return;
    }
    const bytes = new Uint8Array(32);
    window.crypto.getRandomValues(bytes);
    const token = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
    modalDeliveryToken.value = "toki-" + token;
    modalDeliveryToken.dataset.hasToken = "true";
  });

  modalCopyTokenBtn?.addEventListener("click", async () => {
    const token = modalDeliveryToken.value.trim();
    if (!token) return window.alert("Generate a new access key first.");
    try { await navigator.clipboard.writeText(token); window.alert("Access key copied. Store it securely; it cannot be retrieved after this window closes."); }
    catch { window.alert("Clipboard access is unavailable. Select and copy the key manually before saving."); }
  });

  async function sha256Hex(value) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  // Save changes
  modalForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = modalBookingId.value;
    if (!id) return;

    const deliveryUrl = modalDeliveryUrl.value.trim();
    const newDeliveryToken = modalDeliveryToken.value.trim();
    if (newDeliveryToken && (!/^toki-[0-9a-f]{64}$/.test(newDeliveryToken) || !deliveryUrl)) return window.alert("A valid generated access key and a private HTTPS delivery URL are both required.");
    if (deliveryUrl) {
      try { if (new URL(deliveryUrl).protocol !== "https:") throw new Error("HTTPS required"); }
      catch { return window.alert("The private delivery URL must be a valid HTTPS URL."); }
    }
    const payload = {
      status: modalStatusSelect.value,
      confirmed_date: modalConfirmedDate.value || null,
      confirmed_start_time: modalStartTime.value || null,
      confirmed_end_time: modalEndTime.value || null,
      total_price: modalTotalPrice.value ? Number(modalTotalPrice.value) : 0,
      reservation_fee: modalReservationFee.value ? Number(modalReservationFee.value) : 0,
      reservation_fee_paid: modalReservationPaid.checked,
      reservation_fee_paid_at: modalReservationPaid.checked ? new Date().toISOString() : null,
      balance_paid: modalBalancePaid.checked,
      balance_paid_at: modalBalancePaid.checked ? new Date().toISOString() : null,
      delivery_folder_url: deliveryUrl || null,
      admin_notes: modalAdminNotes.value.trim() || null,
      updated_at: new Date().toISOString()
    };

    try {
      if (newDeliveryToken) {
        payload.delivery_token_hash = await sha256Hex(newDeliveryToken);
        payload.delivery_expires_at = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
        payload.delivery_status = "ready";
      } else if (!deliveryUrl && modalDeliveryToken.dataset.hasToken === "true") {
        payload.delivery_token_hash = null; payload.delivery_expires_at = null; payload.delivery_status = "revoked";
      }
      const res = await fetch(SUPABASE_URL + `/rest/v1/toki_booking_requests?id=eq.${id}`, {
        method: "PATCH",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.text();
        alert("Failed to update booking: " + err);
        return;
      }

      closeBookingModal();
      loadBookings();
    } catch (err) {
      alert("Network error updating booking.");
    }
  });

  function escapeHtml(str) {
    return String(str).replace(/[&<>'"]/g, tag => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      "\"": "&quot;"
    }[tag] || tag));
  }

  // Initialize
  initSession();
})();
