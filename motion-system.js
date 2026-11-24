/* TOKI SATSUEI — shared motion orchestration
   Progressive enhancement for homepage and archive, including late-loaded content. */
(() => {
  "use strict";

  const root = document.documentElement;
  if (root.classList.contains("motion-system-ready")) return;

  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  let reduced = preference.matches;
  let observer = null;
  let mutationObserver = null;

  const selector = [
    ".intro-inner > *",
    ".section-heading > div > .eyebrow",
    ".section-heading > div > h2",
    ".section-heading > .section-aside",
    ".work-filters > *",
    ".gallery-card",
    ".gallery-footnote",
    ".frame-intention",
    ".process-heading > *",
    ".process-step",
    ".process-step > *",
    ".service-row",
    ".service-row h3",
    ".service-row p",
    ".service-row .service-arrow",
    ".package-card .package-art > *",
    ".package-card .package-top > *",
    ".package-card h3",
    ".package-card .package-price",
    ".package-card ul",
    ".service-row .service-number",
    ".booking-trust-item",
    ".calculator-wrap",
    ".calc-field-group",
    ".calc-summary-card",
    ".availability-panel",
    ".session-notes > *",
    ".session-notes > div > small",
    ".session-notes > div > p",
    ".about-copy > .eyebrow",
    ".about-copy > h2",
    ".about-copy > p",
    ".about-copy .about-signature",
    ".faq-list details",
    ".contact-copy > .eyebrow",
    ".contact-copy > h2",
    ".contact-copy > p",
    ".contact-copy > .hero-actions",
    ".contact-copy > .contact-small",
    ".inquiry-form > label",
    ".inquiry-form > .form-split",
    ".inquiry-form > .form-submit",
    ".archive-page .album-card",
    ".album-frame",
    ".policy-article",
    ".footer-main > *",
    ".footer-bottom > *",
    ".footer-socials > *",
    ".toki-assurance__grid > *",
    ".toki-advisory",
    ".toki-booking-sheet .booking-fieldset",
    ".toki-booking-sheet .booking-terms-summary",
    ".toki-booking-sheet .booking-verification",
    ".toki-booking-sheet .form-submit"
  ].join(",");

  root.classList.add("motion-system-ready");

  if (!document.querySelector(".toki-film-grain")) {
    const grain = document.createElement("div");
    grain.className = "toki-film-grain";
    grain.setAttribute("aria-hidden", "true");
    document.body.prepend(grain);
  }

  // Optical darkroom overlays: fixed shutter flash curtain + cursor safelight aura (zero layout footprint)
  let shutterCurtain = document.querySelector(".toki-shutter-curtain");
  if (!shutterCurtain) {
    shutterCurtain = document.createElement("div");
    shutterCurtain.className = "toki-shutter-curtain";
    shutterCurtain.setAttribute("aria-hidden", "true");
    shutterCurtain.innerHTML = '<span class="toki-shutter-iris"></span><span class="toki-shutter-streak"></span>';
    document.body.appendChild(shutterCurtain);
  }

  let safelightAura = document.querySelector(".toki-safelight-aura");
  if (!safelightAura) {
    safelightAura = document.createElement("div");
    safelightAura.className = "toki-safelight-aura";
    safelightAura.setAttribute("aria-hidden", "true");
    document.body.appendChild(safelightAura);
  }

  // Precision optical viewfinder SVG reticle injected inside the Hero stage
  const heroArt = document.querySelector(".hero-opening .hero-art");
  if (heroArt && !heroArt.querySelector(".toki-viewfinder-hud")) {
    const hud = document.createElement("div");
    hud.className = "toki-viewfinder-hud";
    hud.setAttribute("aria-hidden", "true");
    hud.innerHTML = `
      <svg class="toki-vf-svg" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice" focusable="false">
        <g class="toki-vf-corners" fill="none" stroke="rgba(236,199,126,0.42)" stroke-width="1.5">
          <path d="M44 108 V44 H108"/>
          <path d="M1092 44 H1156 V108"/>
          <path d="M44 692 V756 H108"/>
          <path d="M1092 756 H1156 V692"/>
        </g>
        <g class="toki-vf-dial" transform="translate(840 370)">
          <circle class="toki-vf-ring-outer" r="195" fill="none" stroke="rgba(245,242,235,0.16)" stroke-width="1" stroke-dasharray="4 10"/>
          <circle class="toki-vf-ring-mid" r="138" fill="none" stroke="rgba(195,42,57,0.45)" stroke-width="1.25" stroke-dasharray="36 18 8 18"/>
          <circle class="toki-vf-ring-inner" r="46" fill="none" stroke="rgba(236,199,126,0.55)" stroke-width="1.2"/>
          <path d="M-22 0 H-7 M7 0 H22 M0 -22 V-7 M0 7 V22" stroke="rgba(236,199,126,0.75)" stroke-width="1.2"/>
          <path d="M-158 0 H-132 M132 0 H158 M0 -158 V-132 M0 132 V158" stroke="rgba(245,242,235,0.34)" stroke-width="1"/>
        </g>
        <g class="toki-vf-rule-ticks" stroke="rgba(245,242,235,0.22)" stroke-width="1">
          <line x1="600" y1="24" x2="600" y2="42"/>
          <line x1="570" y1="28" x2="570" y2="38"/>
          <line x1="630" y1="28" x2="630" y2="38"/>
          <line x1="540" y1="28" x2="540" y2="38"/>
          <line x1="660" y1="28" x2="660" y2="38"/>
        </g>
      </svg>
      <div class="toki-hero-lightleak"></div>
      <div class="toki-hero-scanbeam"></div>
    `;
    heroArt.appendChild(hud);
  }

  const activeAnimations = new WeakMap();
  const transitionTokens = new WeakMap();

  function animate(element, frames, options = {}) {
    if (!element || reduced || typeof element.animate !== "function") return Promise.resolve();
    const previous = activeAnimations.get(element);
    previous?.cancel();
    const animation = element.animate(frames, {
      duration: options.duration ?? 220,
      easing: options.easing ?? "cubic-bezier(.2,.7,.2,1)",
      fill: options.fill ?? "both",
      delay: options.delay ?? 0
    });
    activeAnimations.set(element, animation);
    return animation.finished.catch(() => {}).then(() => {
      if (activeAnimations.get(element) === animation) {
        activeAnimations.delete(element);
        animation.cancel();
      }
    });
  }

  function animateBackdropOut(dialog, duration = 210) {
    if (!dialog?.open || reduced || typeof dialog.animate !== "function") return Promise.resolve();
    try {
      const animation = dialog.animate(
        [{ opacity: 1 }, { opacity: 0 }],
        { duration, easing: "ease-in", fill: "both", pseudoElement: "::backdrop" }
      );
      return animation.finished.catch(() => {}).then(() => animation.cancel());
    } catch (error) {
      return Promise.resolve();
    }
  }

  function animateOut(element, options = {}) {
    const duration = options.duration ?? 220;
    const frames = options.frames ?? [
      { opacity: 1, transform: "translateY(0) scale(1)" },
      { opacity: 0, transform: "translateY(8px) scale(.985)" }
    ];
    return animate(element, frames, { duration, delay: options.delay ?? 0, easing: "ease-in" });
  }

  function swap(element, render, options = {}) {
    if (typeof render !== "function") return Promise.resolve();
    if (!element || reduced) {
      render();
      return Promise.resolve();
    }
    const token = (transitionTokens.get(element) || 0) + 1;
    transitionTokens.set(element, token);
    const duration = options.duration ?? 150;
    return animate(element, [
      { opacity: 1, transform: "translateY(0)" },
      { opacity: 0, transform: "translateY(6px)" }
    ], { duration, easing: "ease-in" }).then(() => {
      if (transitionTokens.get(element) !== token) return;
      render();
      return animate(element, [
        { opacity: 0, transform: "translateY(-5px)" },
        { opacity: 1, transform: "translateY(0)" }
      ], { duration: options.enterDuration ?? 250 });
    });
  }

  function updateText(element, value) {
    if (!element) return;
    const next = String(value ?? "");
    if (element.textContent === next) return;
    if (reduced) {
      element.textContent = next;
      return;
    }
    swap(element, () => { element.textContent = next; }, { duration: 110, enterDuration: 190 });
  }

  const menuTokens = new WeakMap();
  function setMenuOpen(button, nav, open) {
    if (!button || !nav) return Promise.resolve();
    const alreadyOpen = button.getAttribute("aria-expanded") === "true";
    if (alreadyOpen === open) return Promise.resolve();

    const token = (menuTokens.get(nav) || 0) + 1;
    menuTokens.set(nav, token);
    button.setAttribute("aria-expanded", String(open));
    button.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    const links = Array.from(nav.querySelectorAll("a"));

    if (open) {
      nav.classList.add("is-open");
      links.forEach(link => link.classList.add("is-motion-visible"));
      const panel = animate(nav, [
        { opacity: 0, transform: "translateY(-10px) scaleY(.985)", transformOrigin: "top" },
        { opacity: 1, transform: "translateY(0) scaleY(1)", transformOrigin: "top" }
      ], { duration: 260 });
      links.forEach((link, index) => animate(link, [
        { opacity: 0, transform: "translateY(-7px)" },
        { opacity: 1, transform: "translateY(0)" }
      ], { duration: 210, delay: 24 + index * 28 }));
      return panel;
    }

    if (reduced) {
      nav.classList.remove("is-open");
      return Promise.resolve();
    }

    const closing = [
      animateOut(nav, {
        duration: 190,
        frames: [
          { opacity: 1, transform: "translateY(0) scaleY(1)", transformOrigin: "top" },
          { opacity: 0, transform: "translateY(-7px) scaleY(.99)", transformOrigin: "top" }
        ]
      }),
      ...links.map(link => animateOut(link, {
        duration: 190,
        frames: [
          { opacity: 1, transform: "translateY(0)" },
          { opacity: 0, transform: "translateY(-4px)" }
        ]
      }))
    ];
    return Promise.all(closing).then(() => {
      if (menuTokens.get(nav) === token && button.getAttribute("aria-expanded") !== "true") {
        nav.classList.remove("is-open");
      }
    });
  }

  const closingDialogs = new WeakSet();
  function closeDialog(dialog, options = {}) {
    if (!dialog?.open || closingDialogs.has(dialog)) return Promise.resolve();
    closingDialogs.add(dialog);
    const duration = options.duration ?? 220;
    return Promise.all([
      animateOut(dialog, {
        duration,
        frames: [
          { opacity: 1, transform: "translateY(0) scale(1)" },
          { opacity: 0, transform: "translateY(9px) scale(.985)" }
        ]
      }),
      animateBackdropOut(dialog, Math.max(160, duration - 20))
    ]).then(() => {
      if (dialog.open) dialog.close();
    }).finally(() => closingDialogs.delete(dialog));
  }

  let flashLock = 0;
  function triggerShutterFlash(x, y, variant = "gold") {
    if (reduced || !shutterCurtain) return;
    const now = performance.now();
    if (now - flashLock < 140) return;
    flashLock = now;

    const px = typeof x === "number" && Number.isFinite(x) ? x + "px" : "50%";
    const py = typeof y === "number" && Number.isFinite(y) ? y + "px" : "45%";
    shutterCurtain.style.setProperty("--flash-x", px);
    shutterCurtain.style.setProperty("--flash-y", py);
    shutterCurtain.dataset.variant = variant;
    shutterCurtain.classList.remove("is-flashing");
    void shutterCurtain.offsetWidth;
    shutterCurtain.classList.add("is-flashing");

    const iris = shutterCurtain.querySelector(".toki-shutter-iris");
    const streak = shutterCurtain.querySelector(".toki-shutter-streak");
    iris?.animate([
      { opacity: 0.9, transform: "translate(-50%, -50%) scale(0.25)" },
      { opacity: 0.45, transform: "translate(-50%, -50%) scale(1.15)", offset: 0.35 },
      { opacity: 0, transform: "translate(-50%, -50%) scale(2.1)" }
    ], { duration: 480, easing: "cubic-bezier(0.16, 1, 0.3, 1)" });

    streak?.animate([
      { opacity: 0, transform: "translateX(-120%) skewX(-18deg)" },
      { opacity: 0.55, transform: "translateX(0%) skewX(-18deg)", offset: 0.3 },
      { opacity: 0, transform: "translateX(130%) skewX(-18deg)" }
    ], { duration: 520, easing: "cubic-bezier(0.16, 1, 0.3, 1)" });
  }

  function pulseMetric(element) {
    if (!element || reduced || typeof element.animate !== "function") return;
    element.animate([
      { transform: "scale(1)", filter: "brightness(1)", textShadow: "none" },
      { transform: "scale(1.16) translateY(-2px)", filter: "brightness(1.3)", textShadow: "0 0 26px rgba(236, 199, 126, 0.85)" },
      { transform: "scale(0.98)", filter: "brightness(1.06)" },
      { transform: "scale(1)", filter: "brightness(1)", textShadow: "0 0 18px rgba(216, 164, 72, 0.25)" }
    ], { duration: 420, easing: "cubic-bezier(0.16, 1, 0.3, 1)" });
  }

  window.TokiMotion = Object.freeze({
    animate,
    animateOut,
    animateBackdropOut,
    swap,
    updateText,
    setMenuOpen,
    closeDialog,
    triggerShutterFlash,
    pulseMetric,
    get reduced() { return reduced; }
  });

  function reveal(element) {
    element.classList.add("is-motion-visible");
  }

  function unreveal(element) {
    if (!element.contains(document.activeElement)) {
      element.classList.remove("is-motion-visible");
    }
  }

  function prepare(element) {
    if (!(element instanceof HTMLElement)) return;
    if (element.matches("[data-reveal],.reveal-on-scroll,.hero-opening")) return;
    if (element.classList.contains("motion-item")) return;

    element.classList.add("motion-item");
    const siblings = element.parentElement
      ? Array.from(element.parentElement.children).filter(child => child.matches(selector))
      : [];
    const index = Math.max(0, siblings.indexOf(element));
    element.style.setProperty("--motion-delay", Math.min(index, 7) * 58 + "ms");

    if (reduced || !observer) {
      reveal(element);
    } else {
      observer.observe(element);
    }
  }

  function scan(node) {
    if (!node) return;
    if (node instanceof HTMLElement && node.matches(selector)) prepare(node);
    if (typeof node.querySelectorAll === "function") {
      node.querySelectorAll(selector).forEach(prepare);
    }
  }

  if (!reduced && "IntersectionObserver" in window) {
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          reveal(entry.target);
        } else {
          unreveal(entry.target);
        }
      });
    }, {
      threshold: 0.04,
      rootMargin: "0px 0px -3% 0px"
    });
  }

  const interactiveCards = ".toki-card, .package-card, .gallery-card, .process-step, .calculator-wrap, .toki-pillar, .album-card";
  let activeTiltCard = null;
  if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    document.addEventListener("pointermove", event => {
      if (reduced || event.pointerType === "touch") return;
      root.style.setProperty("--aura-x", event.clientX.toFixed(0) + "px");
      root.style.setProperty("--aura-y", event.clientY.toFixed(0) + "px");

      const target = event.target instanceof Element ? event.target : null;
      const card = target?.closest(interactiveCards);
      if (activeTiltCard && activeTiltCard !== card) {
        activeTiltCard.style.removeProperty("--tilt-x");
        activeTiltCard.style.removeProperty("--tilt-y");
      }
      if (!card) {
        activeTiltCard = null;
        return;
      }
      activeTiltCard = card;
      const rect = card.getBoundingClientRect();
      const relX = (event.clientX - rect.left) / Math.max(1, rect.width);
      const relY = (event.clientY - rect.top) / Math.max(1, rect.height);
      card.style.setProperty("--pointer-x", (event.clientX - rect.left).toFixed(1) + "px");
      card.style.setProperty("--pointer-y", (event.clientY - rect.top).toFixed(1) + "px");
      if (!card.classList.contains("calculator-wrap")) {
        const tiltY = ((relX - 0.5) * 9).toFixed(2) + "deg";
        const tiltX = ((0.5 - relY) * 9).toFixed(2) + "deg";
        card.style.setProperty("--tilt-x", tiltX);
        card.style.setProperty("--tilt-y", tiltY);
      }
    }, { passive: true });

    document.addEventListener("pointerleave", () => {
      if (activeTiltCard) {
        activeTiltCard.style.removeProperty("--tilt-x");
        activeTiltCard.style.removeProperty("--tilt-y");
        activeTiltCard = null;
      }
    }, { passive: true });
  }

  // Trigger dramatic shutter flash on major darkroom actions
  document.addEventListener("click", event => {
    if (reduced) return;
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    const trigger = target.closest(".filter-button, .package-card, .package-link, .library-filter, .calc-apply-btn, .hero-opening .button-primary");
    if (trigger) {
      const variant = trigger.closest(".package-card, .calc-apply-btn, .button-primary") ? "crimson" : "gold";
      triggerShutterFlash(event.clientX, event.clientY, variant);
    }
  }, { passive: true });

  // Scroll-linked darkroom parallax & film strip drive
  let scrollFrame = 0;
  function updateScrollParallax() {
    scrollFrame = 0;
    if (reduced) return;
    const sy = window.scrollY || 0;
    const maxScroll = Math.max(1, root.scrollHeight - window.innerHeight);
    const pct = Math.min(1, Math.max(0, sy / maxScroll));
    root.style.setProperty("--scroll-y", sy.toFixed(1));
    root.style.setProperty("--scroll-pct", pct.toFixed(4));
  }
  window.addEventListener("scroll", () => {
    if (!scrollFrame && !reduced) scrollFrame = requestAnimationFrame(updateScrollParallax);
  }, { passive: true });
  updateScrollParallax();

  scan(document);

  if ("MutationObserver" in window) {
    mutationObserver = new MutationObserver(records => {
      records.forEach(record => {
        record.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) scan(node);
        });
      });
    });
    mutationObserver.observe(document.body, { childList: true, subtree: true });
  }

  preference.addEventListener?.("change", event => {
    reduced = event.matches;
    if (reduced) {
      observer?.disconnect();
      document.querySelectorAll(".motion-item").forEach(element => {
        element.classList.add("is-motion-visible");
        element.style.removeProperty("--motion-delay");
      });
      root.style.removeProperty("--scroll-y");
      root.style.removeProperty("--scroll-pct");
    } else if ("IntersectionObserver" in window) {
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) reveal(entry.target);
        });
      }, {
        threshold: 0.08,
        rootMargin: "0px 0px -7% 0px"
      });
      document.querySelectorAll(".motion-item:not(.is-motion-visible)").forEach(element => {
        observer.observe(element);
      });
    }
  });

  window.addEventListener("pagehide", () => {
    observer?.disconnect();
    mutationObserver?.disconnect();
  }, { once: true });
})();
