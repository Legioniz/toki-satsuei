
(() => {
  "use strict";

  const root = document.querySelector("#availability");
  if (!root) return;

  const API_URL = "https://pjuwrngnrrvdiwqspkic.supabase.co/functions/v1/toki-calendar";
  const PUBLISHABLE_KEY = "sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS";
  const $ = (selector) => root.querySelector(selector);
  const monthHeading = $("#availability-month");
  const daysGrid = $("#availability-days");
  const statusText = $("#availability-status");
  const updatedText = $("#availability-updated");
  const countText = $("#availability-count");
  const previousButton = $("#availability-previous");
  const todayButton = $("#availability-today");
  const nextButton = $("#availability-next");
  const retryButton = $("#availability-retry");
  const selectionPanel = $("#availability-selection");
  const selectionDateText = $("#availability-selection-date");
  const useDateButton = $("#availability-use-date");
  const clearDateButton = $("#availability-clear-date");

  const monthFormatter = new Intl.DateTimeFormat("en-PH", { month: "long", year: "numeric", timeZone: "UTC" });
  const dateFormatter = new Intl.DateTimeFormat("en-PH", { dateStyle: "full", timeZone: "UTC" });
  const timeFormatter = new Intl.DateTimeFormat("en-PH", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Manila" });

  function manilaDateKey() {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Manila", year: "numeric", month: "2-digit", day: "2-digit"
    }).formatToParts(new Date());
    const part = (type) => parts.find((item) => item.type === type)?.value || "";
    return part("year") + "-" + part("month") + "-" + part("day");
  }

  function shiftMonth(monthKey, amount) {
    const parts = monthKey.split("-").map(Number);
    return new Date(Date.UTC(parts[0], parts[1] - 1 + amount, 1)).toISOString().slice(0, 7);
  }

  function formatDate(dateKey) {
    return dateFormatter.format(new Date(dateKey + "T00:00:00Z"));
  }

  function dateFromKey(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    return new Date(Date.UTC(year, month - 1, day));
  }

  let displayedMonth = manilaDateKey().slice(0, 7);
  let monthDataKey = "";
  let bookedDates = new Set();
  let loadedForMonth = false;
  let selectedDate = "";
  let requestController = null;
  let refreshInFlight = false;
  let lastSuccessfulRefresh = 0;
  let refreshTimer = null;
  let selectionNotice = "";

  function setStatus(message, state = "live") {
    statusText.textContent = message;
    statusText.dataset.state = state;
  }

  function syncSelection() {
    selectionPanel.hidden = !selectedDate;
    if (selectedDate) selectionDateText.textContent = formatDate(selectedDate);
  }

  function updateNavigation() {
    previousButton.disabled = displayedMonth <= "2000-01";
    nextButton.disabled = displayedMonth >= "2100-12";
    todayButton.disabled = displayedMonth === manilaDateKey().slice(0, 7);
  }

  function renderCalendar() {
    const [year, month] = displayedMonth.split("-").map(Number);
    const today = manilaDateKey();
    monthHeading.textContent = monthFormatter.format(new Date(displayedMonth + "-01T00:00:00Z"));
    daysGrid.setAttribute("aria-label", "Dates in " + monthHeading.textContent);
    daysGrid.setAttribute("aria-busy", String(!loadedForMonth));
    countText.textContent = loadedForMonth
      ? bookedDates.size + " BOOKED " + (bookedDates.size === 1 ? "DAY" : "DAYS")
      : "SYNCING";
    updateNavigation();
    daysGrid.replaceChildren();

    const firstWeekday = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
    const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
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
      const isToday = dateKey === today;
      const isSelected = dateKey === selectedDate;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";
      button.textContent = String(day);
      button.dataset.date = dateKey;
      button.setAttribute("aria-pressed", String(isSelected));
      button.disabled = !loadedForMonth || isBooked || isPast;

      if (isBooked) {
        button.classList.add("is-booked");
        button.setAttribute("aria-label", formatDate(dateKey) + ", confirmed booking");
        button.title = "Confirmed booking";
      } else {
        button.classList.add("is-requestable");
        button.setAttribute("aria-label", formatDate(dateKey) + (isPast ? ", past date" : ", no confirmed booking shown; select to enquire"));
        button.title = isPast ? "Past date" : "Select to enquire about this date";
      }
      if (isToday) button.classList.add("is-today");
      if (isSelected) button.classList.add("is-selected");
      if (isPast) button.classList.add("is-past");
      fragment.appendChild(button);
    }

    daysGrid.appendChild(fragment);
    syncSelection();
  }

  function selectDate(dateKey) {
    if (!loadedForMonth || bookedDates.has(dateKey) || dateKey < manilaDateKey()) return;
    selectedDate = dateKey;
    selectionNotice = "";
    setStatus("Selected " + formatDate(dateKey) + ". Use the date below when you're ready to send an inquiry.");
    renderCalendar();
  }

  function clearSelection() {
    selectedDate = "";
    selectionNotice = "";
    syncSelection();
    renderCalendar();
  }

  function useSelectedDate() {
    if (!selectedDate || bookedDates.has(selectedDate) || selectedDate < manilaDateKey()) {
      clearSelection();
      setStatus("That date is no longer available to request. Choose another unmarked date.", "error");
      return;
    }
    const dateInput = document.querySelector('#inquiry-form input[name="preferred_date"]');
    if (!dateInput) return;
    const chosenDate = selectedDate;
    dateInput.value = chosenDate;
    dateInput.dispatchEvent(new Event("change", { bubbles: true }));
    const formStatus = document.querySelector("#form-status");
    if (formStatus) {
      formStatus.textContent = "You selected " + formatDate(chosenDate) + ". This is an inquiry only; your session is not reserved until we confirm the details with you in writing.";
    }
    document.querySelector("#contact")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start"
    });
    window.setTimeout(() => dateInput.focus({ preventScroll: true }), 350);
  }

  async function fetchMonth(monthKey, signal) {
    const response = await fetch(API_URL + "?month=" + encodeURIComponent(monthKey), {
      method: "GET",
      headers: { "apikey": PUBLISHABLE_KEY },
      cache: "no-store",
      signal
    });
    if (!response.ok) throw new Error(response.status === 429
      ? "The calendar is receiving too many requests. Please retry in a moment."
      : "The calendar service could not be reached.");
    const payload = await response.json();
    if (payload?.ok !== true || payload.month !== monthKey || !Array.isArray(payload.dates)) {
      throw new Error("The calendar returned an incomplete response.");
    }
    const dates = payload.dates.filter((value) => {
      if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value.slice(0, 7) !== monthKey) return false;
      const parsed = dateFromKey(value);
      return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
    });
    return new Set(dates);
  }

  async function refreshCalendar({ quiet = false } = {}) {
    const requestedMonth = displayedMonth;
    if (requestController) requestController.abort();
    const controller = new AbortController();
    requestController = controller;
    const timeout = window.setTimeout(() => controller.abort(), 12000);
    refreshInFlight = true;

    if (monthDataKey !== requestedMonth) {
      monthDataKey = requestedMonth;
      bookedDates = new Set();
      loadedForMonth = false;
    }
    renderCalendar();
    if (!quiet) setStatus("Checking confirmed sessions for " + monthHeading.textContent + "…", "loading");
    retryButton.hidden = true;

    try {
      const nextBookedDates = await fetchMonth(requestedMonth, controller.signal);
      if (requestedMonth !== displayedMonth || controller.signal.aborted) return;

      bookedDates = nextBookedDates;
      loadedForMonth = true;
      lastSuccessfulRefresh = Date.now();
      if (selectedDate && bookedDates.has(selectedDate)) {
        selectionNotice = "The date you selected has since been confirmed by TOKI SATSUEI. Please choose another date.";
        selectedDate = "";
      }
      renderCalendar();
      if (selectionNotice) {
        setStatus(selectionNotice, "error");
        selectionNotice = "";
      } else {
        setStatus("Live schedule synced. Only final dates confirmed in writing are marked as booked.");
      }
      updatedText.textContent = "UPDATED " + timeFormatter.format(new Date()) + " PHT · AUTOMATIC CHECK EVERY MINUTE";
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError" && requestedMonth !== displayedMonth) return;
      if (requestedMonth !== displayedMonth) return;

      if (loadedForMonth) {
        setStatus("Could not refresh. Showing the last successful schedule; retry to check for changes.", "error");
      } else {
        setStatus(error instanceof Error ? error.message : "Live availability could not be loaded.", "error");
        const errorMessage = document.createElement("p");
        errorMessage.className = "calendar-error";
        errorMessage.textContent = "The schedule is temporarily unavailable. No dates can be verified right now.";
        daysGrid.replaceChildren(errorMessage);
        daysGrid.setAttribute("aria-busy", "false");
        countText.textContent = "NOT SYNCED";
      }
      retryButton.hidden = false;
    } finally {
      window.clearTimeout(timeout);
      if (requestController === controller) refreshInFlight = false;
    }
  }

  function syncManilaMonth() {
    const currentMonth = manilaDateKey().slice(0, 7);
    if (displayedMonth !== currentMonth) {
      displayedMonth = currentMonth;
      if (selectedDate && selectedDate.slice(0, 7) !== currentMonth) selectedDate = "";
      selectionNotice = "";
      monthDataKey = "";
      refreshCalendar();
      return true;
    }
    return false;
  }

  function moveFocus(button, offset) {
    const next = dateFromKey(button.dataset.date);
    next.setUTCDate(next.getUTCDate() + offset);
    const nextKey = next.toISOString().slice(0, 10);
    if (nextKey.slice(0, 7) !== displayedMonth) return;
    const target = daysGrid.querySelector('[data-date="' + nextKey + '"]');
    if (target && !target.disabled) target.focus();
  }

  daysGrid.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-date]");
    if (button && !button.disabled) selectDate(button.dataset.date);
  });

  daysGrid.addEventListener("keydown", (event) => {
    const button = event.target.closest("button[data-date]");
    if (!button) return;
    const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
    if (moves[event.key]) {
      event.preventDefault();
      moveFocus(button, moves[event.key]);
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      const day = dateFromKey(button.dataset.date).getUTCDay();
      moveFocus(button, event.key === "Home" ? -day : 6 - day);
    }
  });

  previousButton.addEventListener("click", () => {
    if (previousButton.disabled) return;
    displayedMonth = shiftMonth(displayedMonth, -1);
    monthDataKey = "";
    refreshCalendar();
  });
  nextButton.addEventListener("click", () => {
    if (nextButton.disabled) return;
    displayedMonth = shiftMonth(displayedMonth, 1);
    monthDataKey = "";
    refreshCalendar();
  });
  todayButton.addEventListener("click", () => {
    displayedMonth = manilaDateKey().slice(0, 7);
    if (selectedDate && selectedDate.slice(0, 7) !== displayedMonth) clearSelection();
    monthDataKey = "";
    refreshCalendar();
  });
  retryButton.addEventListener("click", () => {
    if (!refreshInFlight) refreshCalendar();
  });
  useDateButton.addEventListener("click", useSelectedDate);
  clearDateButton.addEventListener("click", clearSelection);

  renderCalendar();
  refreshCalendar();

  refreshTimer = window.setInterval(() => {
    if (!syncManilaMonth() && !refreshInFlight) refreshCalendar({ quiet: true });
  }, 60000);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    if (!syncManilaMonth() && !refreshInFlight && Date.now() - lastSuccessfulRefresh > 30000) {
      refreshCalendar({ quiet: true });
    }
  });
})();
