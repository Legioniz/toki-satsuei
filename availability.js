
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
  const bookedSlotsList = $("#availability-booked-slot-list");
  const bookedSlotsNote = $("#availability-booked-slot-note");
  const useDateButton = $("#availability-use-date");
  const clearDateButton = $("#availability-clear-date");

  const monthFormatter = new Intl.DateTimeFormat("en-PH", { month: "long", year: "numeric", timeZone: "UTC" });
  const dateFormatter = new Intl.DateTimeFormat("en-PH", { dateStyle: "full", timeZone: "UTC" });
  const slotTimeFormatter = new Intl.DateTimeFormat("en-PH", { hour: "numeric", minute: "2-digit", timeZone: "UTC" });
  const clockTimeFormatter = new Intl.DateTimeFormat("en-PH", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Manila" });
  const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
  const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$/;

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

  function dateFromKey(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    return new Date(Date.UTC(year, month - 1, day));
  }

  function formatDate(dateKey) {
    return dateFormatter.format(dateFromKey(dateKey));
  }

  function formatTime(timeValue) {
    const normalized = timeValue.length === 5 ? timeValue + ":00" : timeValue;
    return slotTimeFormatter.format(new Date("1970-01-01T" + normalized + "Z"));
  }

  function bookingCount() {
    let total = 0;
    for (const slots of bookingsByDate.values()) total += slots.length;
    return total;
  }

  let displayedMonth = manilaDateKey().slice(0, 7);
  let monthDataKey = "";
  let bookingsByDate = new Map();
  let loadedForMonth = false;
  let selectedDate = "";
  let requestController = null;
  let refreshInFlight = false;
  let lastSuccessfulRefresh = 0;
  let selectionNotice = "";

  function setStatus(message, state = "live") {
    statusText.textContent = message;
    statusText.dataset.state = state;
  }

  function syncSelection() {
    selectionPanel.hidden = !selectedDate;
    if (!selectedDate) return;

    selectionDateText.textContent = formatDate(selectedDate);
    const slots = bookingsByDate.get(selectedDate) || [];
    bookedSlotsList.replaceChildren();

    if (slots.length) {
      slots.forEach((slot, index) => {
        const item = document.createElement("li");
        const number = document.createElement("span");
        const time = document.createElement("strong");
        number.className = "availability-slot-number";
        number.textContent = String(index + 1).padStart(2, "0");
        time.textContent = formatTime(slot.start_time) + " – " + formatTime(slot.end_time);
        item.append(number, time);
        bookedSlotsList.appendChild(item);
      });
      bookedSlotsNote.textContent = slots.length + " confirmed time " + (slots.length === 1 ? "window is" : "windows are") + " already booked. Other non-overlapping sessions may still be requested, subject to confirmation.";
    } else {
      const item = document.createElement("li");
      item.className = "availability-no-slots";
      item.textContent = "No confirmed time windows listed yet";
      bookedSlotsList.appendChild(item);
      bookedSlotsNote.textContent = "This date has no confirmed session times shown. Your requested schedule still needs written confirmation.";
    }
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
    daysGrid.setAttribute("role", "grid");
    countText.textContent = loadedForMonth
      ? bookingCount() + " BOOKED " + (bookingCount() === 1 ? "SLOT" : "SLOTS")
      : "SYNCING";
    updateNavigation();
    daysGrid.replaceChildren();

    const firstWeekday = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
    const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
    const fragment = document.createDocumentFragment();

    for (let blank = 0; blank < firstWeekday; blank += 1) {
      const spacer = document.createElement("span");
      spacer.className = "calendar-day-empty";
      spacer.setAttribute("role", "gridcell");
      spacer.setAttribute("aria-hidden", "true");
      fragment.appendChild(spacer);
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const dateKey = displayedMonth + "-" + String(day).padStart(2, "0");
      const slots = bookingsByDate.get(dateKey) || [];
      const hasBookings = slots.length > 0;
      const isPast = dateKey < today;
      const isToday = dateKey === today;
      const isSelected = dateKey === selectedDate;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";
      button.setAttribute("role", "gridcell");
      button.textContent = String(day);
      button.dataset.date = dateKey;
      button.setAttribute("aria-pressed", String(isSelected));
      button.disabled = !loadedForMonth || isPast;

      if (hasBookings) {
        button.classList.add("is-booked");
        const times = slots.map((slot) => formatTime(slot.start_time) + " to " + formatTime(slot.end_time)).join(", ");
        button.setAttribute("aria-label", formatDate(dateKey) + ", " + slots.length + " confirmed time " + (slots.length === 1 ? "window: " : "windows: ") + times + ". Select to view schedule.");
        button.title = slots.length + " booked time " + (slots.length === 1 ? "window" : "windows") + " — select to view";
        const count = document.createElement("span");
        count.className = "calendar-booking-count";
        count.setAttribute("aria-hidden", "true");
        count.textContent = slots.length > 9 ? "9+" : String(slots.length);
        button.appendChild(count);
      } else {
        button.classList.add("is-requestable");
        button.setAttribute("aria-label", formatDate(dateKey) + (isPast ? ", past date" : ", no confirmed time windows shown; select to enquire"));
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
    if (!loadedForMonth || dateKey < manilaDateKey()) return;
    selectedDate = dateKey;
    selectionNotice = "";
    const slots = bookingsByDate.get(dateKey) || [];
    if (slots.length) {
      setStatus(formatDate(dateKey) + " has " + slots.length + " confirmed time " + (slots.length === 1 ? "window" : "windows") + " already booked. Other non-overlapping session times may still be requested.");
    } else {
      setStatus("Selected " + formatDate(dateKey) + ". No confirmed time windows are listed yet; the requested schedule still needs confirmation.");
    }
    renderCalendar();
  }

  function clearSelection() {
    selectedDate = "";
    selectionNotice = "";
    syncSelection();
    renderCalendar();
  }

  function useSelectedDate() {
    if (!selectedDate || selectedDate.slice(0, 7) !== displayedMonth || !loadedForMonth || selectedDate < manilaDateKey()) {
      clearSelection();
      setStatus("That date can no longer be selected. Choose another future date.", "error");
      return;
    }
    const dateInput = document.querySelector('#inquiry-form input[name="preferred_date"]');
    if (!dateInput) return;

    const chosenDate = selectedDate;
    const slots = bookingsByDate.get(chosenDate) || [];
    dateInput.value = chosenDate;
    dateInput.dispatchEvent(new Event("change", { bubbles: true }));

    const formStatus = document.querySelector("#form-status");
    if (formStatus) {
      const slotNotice = slots.length
        ? " This date already has " + slots.length + " confirmed time " + (slots.length === 1 ? "window" : "windows") + " shown in the calendar; you may request another non-overlapping time."
        : "";
      formStatus.textContent = "You selected " + formatDate(chosenDate) + "." + slotNotice + " This is an inquiry only; your session is not reserved until we confirm the details with you in writing.";
    }

    document.querySelector("#contact")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start"
    });
    window.setTimeout(() => dateInput.focus({ preventScroll: true }), 350);
  }

  // Errors whose message is safe to show visitors. Anything else (raw browser
  // messages such as "Failed to fetch") is replaced with a plain fallback.
  function friendlyError(message) {
    const error = new Error(message);
    error.friendly = true;
    return error;
  }

  async function fetchMonth(monthKey, signal) {
    let response;
    try {
      response = await fetch(API_URL + "?month=" + encodeURIComponent(monthKey), {
        method: "GET",
        headers: { "apikey": PUBLISHABLE_KEY },
        cache: "no-store",
        signal
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      throw friendlyError("The calendar service could not be reached.");
    }
    if (!response.ok) {
      throw friendlyError(response.status === 429
        ? "The calendar is receiving too many requests. Please retry in a moment."
        : "The calendar service could not be reached.");
    }

    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw friendlyError("The calendar returned an incomplete booking schedule.");
    }
    if (payload?.ok !== true || payload.month !== monthKey || !Array.isArray(payload.bookings)) {
      throw friendlyError("The calendar returned an incomplete booking schedule.");
    }

    const nextBookings = new Map();
    payload.bookings.forEach((booking) => {
      if (!booking || typeof booking.date !== "string" || !DATE_PATTERN.test(booking.date) || booking.date.slice(0, 7) !== monthKey) return;
      if (typeof booking.start_time !== "string" || typeof booking.end_time !== "string") return;
      if (!TIME_PATTERN.test(booking.start_time) || !TIME_PATTERN.test(booking.end_time)) return;
      const start = booking.start_time.length === 5 ? booking.start_time + ":00" : booking.start_time;
      const end = booking.end_time.length === 5 ? booking.end_time + ":00" : booking.end_time;
      if (start >= end) return;

      const day = dateFromKey(booking.date);
      if (!Number.isFinite(day.getTime()) || day.toISOString().slice(0, 10) !== booking.date) return;
      const slots = nextBookings.get(booking.date) || [];
      slots.push({ start_time: start, end_time: end });
      nextBookings.set(booking.date, slots);
    });

    for (const slots of nextBookings.values()) {
      slots.sort((a, b) => a.start_time.localeCompare(b.start_time));
    }
    return nextBookings;
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
      bookingsByDate = new Map();
      loadedForMonth = false;
    }
    renderCalendar();
    if (!quiet) setStatus("Checking confirmed time windows for " + monthHeading.textContent + "…", "loading");
    retryButton.hidden = true;

    try {
      const nextBookings = await fetchMonth(requestedMonth, controller.signal);
      if (requestedMonth !== displayedMonth || controller.signal.aborted) return;

      bookingsByDate = nextBookings;
      loadedForMonth = true;
      lastSuccessfulRefresh = Date.now();
      renderCalendar();

      if (selectionNotice) {
        setStatus(selectionNotice, "error");
        selectionNotice = "";
      } else if (bookingCount() === 0) {
        setStatus("No confirmed time windows are listed for this month yet. Dates remain subject to confirmation.");
      } else {
        setStatus("Live schedule synced. Booked time windows are shown on each date; non-overlapping sessions may share a day.");
      }
      updatedText.textContent = "UPDATED " + clockTimeFormatter.format(new Date()) + " PHT · AUTOMATIC CHECK EVERY MINUTE";
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError" && requestedMonth !== displayedMonth) return;
      if (requestedMonth !== displayedMonth) return;

      if (loadedForMonth) {
        setStatus("Could not refresh. Showing the last successful schedule; retry to check for changes.", "error");
      } else {
        setStatus((error && error.friendly ? error.message : "The live schedule could not be loaded.") + " Message us to check a date.", "error");
        updatedText.textContent = "Schedule unavailable. Message us to check a date.";
        const errorMessage = document.createElement("p");
        errorMessage.className = "calendar-error";
        errorMessage.textContent = "The schedule is temporarily unavailable. No booked times can be verified right now.";
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
    if (selectedDate && selectedDate.slice(0, 7) !== displayedMonth) selectedDate = "";
    monthDataKey = "";
    refreshCalendar();
  });
  nextButton.addEventListener("click", () => {
    if (nextButton.disabled) return;
    displayedMonth = shiftMonth(displayedMonth, 1);
    if (selectedDate && selectedDate.slice(0, 7) !== displayedMonth) selectedDate = "";
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

  window.setInterval(() => {
    if (!syncManilaMonth() && !refreshInFlight) refreshCalendar({ quiet: true });
  }, 60000);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    if (!syncManilaMonth() && !refreshInFlight && Date.now() - lastSuccessfulRefresh > 30000) {
      refreshCalendar({ quiet: true });
    }
  });
})();
