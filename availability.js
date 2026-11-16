
(() => {
  "use strict";

  const root = document.querySelector("#availability");
  if (!root) return;

  const API_URL = "https://pjuwrngnrrvdiwqspkic.supabase.co/functions/v1/toki-calendar";
  const PUBLISHABLE_KEY = "sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS";
  const monthHeading = root.querySelector("#availability-month");
  const daysGrid = root.querySelector("#availability-days");
  const statusText = root.querySelector("#availability-status");
  const updatedText = root.querySelector("#availability-updated");
  const previousButton = root.querySelector("#availability-previous");
  const nextButton = root.querySelector("#availability-next");

  const monthFormatter = new Intl.DateTimeFormat("en-PH", {
    month: "long", year: "numeric", timeZone: "UTC"
  });
  const dateFormatter = new Intl.DateTimeFormat("en-PH", {
    dateStyle: "full", timeZone: "UTC"
  });
  const timeFormatter = new Intl.DateTimeFormat("en-PH", {
    hour: "numeric", minute: "2-digit", timeZone: "Asia/Manila"
  });

  function manilaDateKey() {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Manila", year: "numeric", month: "2-digit", day: "2-digit"
    }).formatToParts(new Date());
    const part = (type) => parts.find((item) => item.type === type)?.value || "";
    return part("year") + "-" + part("month") + "-" + part("day");
  }

  function shiftMonth(monthKey, amount) {
    const parts = monthKey.split("-").map(Number);
    const shifted = new Date(Date.UTC(parts[0], parts[1] - 1 + amount, 1));
    return shifted.toISOString().slice(0, 7);
  }

  function monthTitle(monthKey) {
    return monthFormatter.format(new Date(monthKey + "-01T00:00:00Z"));
  }

  function formatDate(dateKey) {
    return dateFormatter.format(new Date(dateKey + "T00:00:00Z"));
  }

  let displayedMonth = manilaDateKey().slice(0, 7);
  let monthDataKey = "";
  let bookedDates = new Set();
  let loadedForMonth = false;
  let selectedDate = "";
  let requestController = null;

  function setStatus(message, state) {
    statusText.textContent = message;
    statusText.dataset.state = state || "live";
  }

  function renderCalendar() {
    const parts = displayedMonth.split("-").map(Number);
    const year = parts[0];
    const month = parts[1];
    monthHeading.textContent = monthTitle(displayedMonth);
    daysGrid.setAttribute("aria-label", "Dates in " + monthHeading.textContent);
    daysGrid.setAttribute("aria-busy", String(!loadedForMonth));
    daysGrid.replaceChildren();

    const firstWeekday = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
    const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
    const today = manilaDateKey();
    const fragment = document.createDocumentFragment();

    for (let blank = 0; blank < firstWeekday; blank += 1) {
      const spacer = document.createElement("span");
      spacer.className = "calendar-day-empty";
      spacer.setAttribute("aria-hidden", "true");
      fragment.appendChild(spacer);
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const dateKey = displayedMonth + "-" + String(day).padStart(2, "0");
      const isBooked = bookedDates.has(dateKey);
      const isPast = dateKey < today;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";
      button.textContent = String(day);
      button.dataset.date = dateKey;
      button.disabled = !loadedForMonth || isBooked || isPast;
      if (isBooked) {
        button.classList.add("is-booked");
        button.setAttribute("aria-label", formatDate(dateKey) + ", confirmed booking");
        button.title = "Confirmed booking";
      } else {
        button.setAttribute("aria-label", formatDate(dateKey) + (isPast ? ", past date" : ", inquire about this date"));
        button.title = isPast ? "Past date" : "Select this date for an inquiry";
      }
      if (dateKey === today) button.classList.add("is-today");
      if (dateKey === selectedDate) button.classList.add("is-selected");
      if (isPast) button.classList.add("is-past");
      button.addEventListener("click", () => selectDate(dateKey));
      fragment.appendChild(button);
    }
    daysGrid.appendChild(fragment);
  }

  function selectDate(dateKey) {
    if (!loadedForMonth || bookedDates.has(dateKey) || dateKey < manilaDateKey()) return;
    const dateInput = document.querySelector('#inquiry-form input[name="preferred_date"]');
    if (!dateInput) return;
    selectedDate = dateKey;
    dateInput.value = dateKey;
    dateInput.dispatchEvent(new Event("change", { bubbles: true }));
    const formStatus = document.querySelector("#form-status");
    if (formStatus) {
      formStatus.textContent = "You selected " + formatDate(dateKey) + ". This is an inquiry only; your session is not reserved until we confirm the details with you in writing.";
    }
    renderCalendar();
    const contact = document.querySelector("#contact");
    contact?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    window.setTimeout(() => dateInput.focus({ preventScroll: true }), 350);
  }

  async function refreshCalendar() {
    const requestedMonth = displayedMonth;
    if (monthDataKey !== requestedMonth) {
      monthDataKey = requestedMonth;
      bookedDates = new Set();
      loadedForMonth = false;
      renderCalendar();
    }

    if (requestController) requestController.abort();
    requestController = new AbortController();
    const controller = requestController;

    try {
      const url = API_URL + "?month=" + encodeURIComponent(requestedMonth);
      const response = await fetch(url, {
        method: "GET",
        headers: { "apikey": PUBLISHABLE_KEY },
        cache: "no-store",
        signal: controller.signal
      });
      if (!response.ok) throw new Error("Calendar request failed");
      const payload = await response.json();
      if (payload?.ok !== true || payload.month !== requestedMonth || !Array.isArray(payload.dates)) {
        throw new Error("Calendar response was incomplete");
      }
      if (requestedMonth !== displayedMonth) return;

      bookedDates = new Set(payload.dates.filter((value) =>
        typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && value.slice(0, 7) === requestedMonth
      ));
      loadedForMonth = true;
      renderCalendar();
      setStatus("Only bookings confirmed in writing are marked. Unmarked dates still need confirmation.", "live");
      updatedText.textContent = "LAST CHECKED " + timeFormatter.format(new Date()) + " PHT · AUTO-REFRESH EVERY MINUTE";
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (requestedMonth !== displayedMonth) return;
      if (loadedForMonth) {
        setStatus("The latest refresh did not complete. Showing the last successful check.", "error");
      } else {
        setStatus("Availability could not be loaded. Please message us before choosing a date.", "error");
        const errorMessage = document.createElement("p");
        errorMessage.className = "calendar-error";
        errorMessage.textContent = "The live calendar is temporarily unavailable. Please contact us to check a date.";
        daysGrid.replaceChildren(errorMessage);
        daysGrid.setAttribute("aria-busy", "false");
      }
    }
  }

  function syncManilaMonth() {
    const currentMonth = manilaDateKey().slice(0, 7);
    if (displayedMonth !== currentMonth) {
      displayedMonth = currentMonth;
      selectedDate = "";
      refreshCalendar();
      return true;
    }
    return false;
  }

  previousButton.addEventListener("click", () => {
    displayedMonth = shiftMonth(displayedMonth, -1);
    refreshCalendar();
  });
  nextButton.addEventListener("click", () => {
    displayedMonth = shiftMonth(displayedMonth, 1);
    refreshCalendar();
  });

  renderCalendar();
  refreshCalendar();

  window.setInterval(() => {
    if (!syncManilaMonth()) refreshCalendar();
  }, 60000);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && !syncManilaMonth()) refreshCalendar();
  });
})();
