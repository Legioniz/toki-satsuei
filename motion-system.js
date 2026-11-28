/* TOKI SATSUEI — unified scroll choreography, darkroom optics & reduced-motion engine. */
(() => {
  "use strict";

  const root = document.documentElement;
  if (root.classList.contains("motion-system-ready")) return;

  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  const fineHover = window.matchMedia("(hover: hover) and (pointer: fine)");
  let reduced = preference.matches;
  let observer = null;
  let mutationObserver = null;

  /* Map each selector group to its motion profile and reveal timing role. */
  const MOTION_PROFILES = [
    {
      profile: "develop-print",
      selectors: [".gallery-card", ".album-card", ".album-frame", ".about-visual"]
    },
    {
      profile: "spring-card",
      selectors: [
        ".package-card", ".process-step", ".toki-pillar",
        ".booking-trust-item", ".toki-advisory", ".calc-summary-card"
      ]
    },
    {
      profile: "aperture-iris",
      selectors: [
        ".calculator-wrap", ".availability-panel", ".frame-intention",
        ".session-flexible-duration", ".booking-terms-summary",
        ".booking-expectation", ".policy-disclaimer", ".contact-copy"
      ]
    },
    {
      profile: "focus-pull",
      selectors: [
        ".section-heading h2", ".policy-hero h1",
        ".archive-head h1", ".contact-copy h2"
      ]
    },
    {
      profile: "film-gate",
      selectors: [
        ".archive-group", ".policy-article",
        ".admin-metric-card", ".client-session-banner",
        ".booking-reference-card"
      ]
    },
    {
      profile: "editorial-unfold",
      selectors: [
        ".intro-inner > *", ".section-heading > div > .eyebrow",
        ".section-heading > div > h2", ".section-heading > .section-aside",
        ".work-filters > *", ".gallery-footnote", ".process-heading > *",
        ".service-row", ".session-notes > div", ".calc-field-group",
        ".about-copy > *", ".faq-list details", ".faq-aside",
        ".inquiry-form > label", ".inquiry-form > .form-split",
        ".toki-booking-sheet .booking-fieldset",
        ".toki-booking-sheet .booking-fieldset > label",
        ".toki-booking-sheet .booking-fieldset .form-split > label",
        ".toki-booking-sheet .booking-consent",
        ".toki-booking-sheet .booking-verification",
        ".toki-booking-sheet .form-submit",
        ".policy-hero > *", ".policy-article", ".policy-index",
        ".archive-head > *", ".footer-main > *", ".footer-bottom > *",
        ".footer-socials > *"
      ]
    }
  ];

  const ALL_SELECTOR = MOTION_PROFILES.flatMap(group => group.selectors).join(",");
  const SCROLL_TRACKED_SELECTOR = [
    ".hero-opening", ".about-visual", ".frame-intention",
    ".calculator-wrap", ".availability-panel", ".booking-trust-bar",
    ".toki-assurance", ".policy-hero", ".archive-head"
  ].join(",");
  const SCROLL_SCENE_SELECTOR = [
    ".hero-opening", ".intro-band", ".work-section", ".services-section",
    ".sessions-section", ".availability-section", ".process-section",
    ".about-section", ".faq-section", ".contact-section",
    ".archive-head", ".archive-group", ".policy-hero", ".policy-article",
    ".not-found-main", ".admin-main", ".client-main"
  ].join(",");
  const SCROLL_PARALLAX_SELECTOR = [
    ".hero-opening .hero-photo",
    ".about-visual img",
    ".gallery-card .gallery-image img"
  ].join(",");

  let scrollScenes = [];
  let scrollTracked = [];
  let scrollParallax = [];

  function refreshScrollTargets() {
    scrollScenes = Array.from(document.querySelectorAll(SCROLL_SCENE_SELECTOR));
    scrollTracked = Array.from(document.querySelectorAll(SCROLL_TRACKED_SELECTOR));
    scrollParallax = Array.from(document.querySelectorAll(SCROLL_PARALLAX_SELECTOR));
  }

  root.classList.add("motion-system-ready", "motion-ready");

  /* Shorten site motion without changing the official startup logo sequence. */
  const MOTION_DURATION_FACTOR = 0.78;
  const CSS_MOTION_PLAYBACK_RATE = 1.28;
  const STARTUP_LOGO_SELECTOR = ".toki-intro-curtain, .toki-intro-curtain *, .toki-intro-logo";

  function isStartupLogoAnimation(animation) {
    if (String(animation?.animationName || "").startsWith("tokiIntro")) return true;
    const target = animation?.effect?.target;
    if (!target || target.nodeType !== Node.ELEMENT_NODE) return false;
    return target.matches(STARTUP_LOGO_SELECTOR) ||
      Boolean(target.closest(".toki-intro-curtain"));
  }

  function accelerateAnimation(animation) {
    if (reduced || !animation || isStartupLogoAnimation(animation)) return;
    if (Math.abs(animation.playbackRate - CSS_MOTION_PLAYBACK_RATE) < 0.001) return;
    try {
      if (typeof animation.updatePlaybackRate === "function") {
        animation.updatePlaybackRate(CSS_MOTION_PLAYBACK_RATE);
      } else {
        animation.playbackRate = CSS_MOTION_PLAYBACK_RATE;
      }
    } catch {
      /* Keep the original effect if a browser rejects a playback-rate update. */
    }
  }

  function accelerateRunningAnimations() {
    if (reduced || typeof document.getAnimations !== "function") return;
    document.getAnimations().forEach(accelerateAnimation);
  }

  function accelerateAnimationsOnEvent(event) {
    if (reduced || !event.target || typeof event.target.getAnimations !== "function") return;
    event.target.getAnimations().forEach(accelerateAnimation);
  }

  document.addEventListener("animationstart", accelerateAnimationsOnEvent, true);
  document.addEventListener("transitionrun", accelerateAnimationsOnEvent, true);
  accelerateRunningAnimations();

  function shortenMotionTime(value) {
    return typeof value === "number" && Number.isFinite(value) && value > 0
      ? Math.max(80, Math.round(value * MOTION_DURATION_FACTOR))
      : value;
  }

  function shortenMotionDelay(value) {
    return typeof value === "number" && Number.isFinite(value) && value > 0
      ? Math.round(value * MOTION_DURATION_FACTOR)
      : value;
  }

  /* Resolve profile name for an element, respecting explicit markup attributes. */
  function resolveProfile(element) {
    if (element.dataset.motion) return element.dataset.motion;
    for (const entry of MOTION_PROFILES) {
      if (entry.selectors.some(sel => element.matches(sel))) return entry.profile;
    }
    return "editorial-unfold";
  }

  /* Inject non-layout optical chrome overlays once. */
  function playPageIntroGraphic() {
    if (reduced || !document.body || document.querySelector(".toki-intro-curtain")) return;
    const curtain = document.createElement("div");
    curtain.className = "toki-intro-curtain";
    curtain.setAttribute("aria-hidden", "true");
    curtain.innerHTML = `
      <div class="toki-intro-stage">
        <svg class="toki-intro-aperture" viewBox="0 0 220 220" focusable="false">
          <circle class="toki-intro-ring-outer" cx="110" cy="110" r="98" fill="none" stroke="rgba(245,242,235,0.28)" stroke-width="1" stroke-dasharray="5 9"/>
          <circle class="toki-intro-ring-crimson" cx="110" cy="110" r="78" fill="none" stroke="rgba(195,42,57,0.82)" stroke-width="1.8" stroke-dasharray="48 16 14 16"/>
          <circle class="toki-intro-ring-gold" cx="110" cy="110" r="56" fill="none" stroke="rgba(245,242,235,0.72)" stroke-width="1.2"/>
          <g class="toki-intro-blades" stroke="rgba(245,242,235,0.34)" stroke-width="1">
            <line x1="110" y1="8" x2="110" y2="30"/>
            <line x1="110" y1="190" x2="110" y2="212"/>
            <line x1="8" y1="110" x2="30" y2="110"/>
            <line x1="190" y1="110" x2="212" y2="110"/>
            <line x1="38" y1="38" x2="54" y2="54"/>
            <line x1="166" y1="166" x2="182" y2="182"/>
            <line x1="182" y1="38" x2="166" y2="54"/>
            <line x1="54" y1="166" x2="38" y2="182"/>
          </g>
        </svg>
        <div class="toki-intro-seal">
          <img class="toki-intro-logo" src="./assets/brand/Toki-Satsuei-Brushstroke-Emblem.png" alt="" decoding="async" fetchpriority="high">
        </div>
        <span class="toki-intro-sweep"></span>
      </div>
    `;
    document.body.prepend(curtain);
    let cleaned = false;
    const cleanup = () => {
      if (cleaned) return;
      cleaned = true;
      curtain.remove();
    };
    curtain.addEventListener("animationend", event => {
      if (event.target === curtain) cleanup();
    });
    window.setTimeout(cleanup, 850);
  }

  function ensureDarkroomOverlays() {
    playPageIntroGraphic();
    if (!document.querySelector(".toki-film-grain")) {
      const grain = document.createElement("div");
      grain.className = "toki-film-grain";
      grain.setAttribute("aria-hidden", "true");
      document.body.prepend(grain);
    }

    if (!document.querySelector(".toki-shutter-curtain")) {
      const curtain = document.createElement("div");
      curtain.className = "toki-shutter-curtain";
      curtain.setAttribute("aria-hidden", "true");
      curtain.innerHTML = '<span class="toki-shutter-iris"></span><span class="toki-shutter-streak"></span>';
      document.body.append(curtain);
    }

    if (!document.querySelector(".toki-safelight-aura")) {
      const aura = document.createElement("div");
      aura.className = "toki-safelight-aura";
      aura.setAttribute("aria-hidden", "true");
      document.body.append(aura);
    }

    const heroArt = document.querySelector(".hero-opening .hero-art");
    if (heroArt && !heroArt.querySelector(".toki-viewfinder-hud")) {
      const hud = document.createElement("div");
      hud.className = "toki-viewfinder-hud";
      hud.setAttribute("aria-hidden", "true");
      hud.innerHTML = `
        <svg class="toki-vf-svg" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice" focusable="false">
          <g class="toki-vf-corners" fill="none" stroke="rgba(245,242,235,0.38)" stroke-width="1.5">
            <path d="M44 108 V44 H108"/>
            <path d="M1092 44 H1156 V108"/>
            <path d="M44 692 V756 H108"/>
            <path d="M1092 756 H1156 V692"/>
          </g>
          <g class="toki-vf-dial" transform="translate(840 370)">
            <circle class="toki-vf-ring-outer" r="195" fill="none" stroke="rgba(245,242,235,0.17)" stroke-width="1" stroke-dasharray="4 10"/>
            <circle class="toki-vf-ring-mid" r="138" fill="none" stroke="rgba(195,42,57,0.52)" stroke-width="1.25" stroke-dasharray="36 18 8 18"/>
            <circle class="toki-vf-ring-inner" r="46" fill="none" stroke="rgba(245,242,235,0.52)" stroke-width="1.2"/>
            <path d="M-22 0 H-7 M7 0 H22 M0 -22 V-7 M0 7 V22" stroke="rgba(195,42,57,0.85)" stroke-width="1.4"/>
            <path d="M-158 0 H-132 M132 0 H158 M0 -158 V-132 M0 132 V158" stroke="rgba(245,242,235,0.34)" stroke-width="1"/>
          </g>
          <g class="toki-vf-rule-ticks" stroke="rgba(245,242,235,0.24)" stroke-width="1">
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
      heroArt.append(hud);
    }
  }

  ensureDarkroomOverlays();
  const shutterCurtain = document.querySelector(".toki-shutter-curtain");

  /* WAAPI helpers kept under clean weak-map lifecycle control. */
  const activeAnimations = new WeakMap();
  const transitionTokens = new WeakMap();

  function animate(element, frames, options = {}) {
    if (!element || reduced || typeof element.animate !== "function") return Promise.resolve();
    const previous = activeAnimations.get(element);
    previous?.cancel();
    const animation = element.animate(frames, {
      duration: shortenMotionTime(options.duration ?? 220),
      easing: options.easing ?? "cubic-bezier(0.2, 0.7, 0.2, 1)",
      fill: options.fill ?? "both",
      delay: shortenMotionDelay(options.delay ?? 0)
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
        { duration: shortenMotionTime(duration), easing: "ease-in", fill: "both", pseudoElement: "::backdrop" }
      );
      return animation.finished.catch(() => {}).then(() => animation.cancel());
    } catch {
      return Promise.resolve();
    }
  }

  function animateOut(element, options = {}) {
    const duration = options.duration ?? 220;
    const frames = options.frames ?? [
      { opacity: 1, transform: "translateY(0) scale(1)" },
      { opacity: 0, transform: "translateY(8px) scale(0.985)" }
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
      // Reset after display:flex takes effect so hidden drawers cannot retain stale scroll.
      nav.scrollTop = 0;
      nav.scrollLeft = 0;
      links.forEach(link => link.classList.add("is-motion-visible"));
      const panel = animate(nav, [
        { opacity: 0, transform: "translateY(-10px) scaleY(0.985)", transformOrigin: "top" },
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
          { opacity: 0, transform: "translateY(-7px) scaleY(0.99)", transformOrigin: "top" }
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
          { opacity: 0, transform: "translateY(9px) scale(0.985)" }
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
    ], { duration: shortenMotionTime(480), easing: "cubic-bezier(0.16, 1, 0.3, 1)" });

    streak?.animate([
      { opacity: 0, transform: "translateX(-120%) skewX(-18deg)" },
      { opacity: 0.55, transform: "translateX(0%) skewX(-18deg)", offset: 0.3 },
      { opacity: 0, transform: "translateX(130%) skewX(-18deg)" }
    ], { duration: shortenMotionTime(520), easing: "cubic-bezier(0.16, 1, 0.3, 1)" });
  }

  function pulseMetric(element) {
    if (!element || reduced || typeof element.animate !== "function") return;
    element.animate([
      { transform: "scale(1)", filter: "brightness(1)", textShadow: "none" },
      { transform: "scale(1.18) translateY(-3px)", filter: "brightness(1.25)", textShadow: "0 0 24px rgba(195, 42, 57, 0.85)" },
      { transform: "scale(0.97)", filter: "brightness(1.06)" },
      { transform: "scale(1)", filter: "brightness(1)", textShadow: "0 0 14px rgba(195, 42, 57, 0.25)" }
    ], { duration: shortenMotionTime(460), easing: "cubic-bezier(0.34, 1.48, 0.64, 1)" });
  }

  /* Unified intersection & scroll visibility management for [data-reveal] + .motion-item. */
  function markVisible(element) {
    if (element.hasAttribute("data-reveal")) element.classList.add("is-visible");
    if (element.classList.contains("motion-item")) element.classList.add("is-motion-visible");
  }

  const INTERACTIVE_LOCKED = ".availability-panel, .calculator-wrap, .toki-booking-sheet, .booking-fieldset";

  function markHidden(element) {
    if (element.contains(document.activeElement)) return;
    if (element.matches(INTERACTIVE_LOCKED)) return;
    if (element.hasAttribute("data-reveal")) element.classList.remove("is-visible");
    if (element.classList.contains("motion-item")) element.classList.remove("is-motion-visible");
  }

  function matchingElements(node, selector) {
    const matches = [];
    if (node instanceof Element && node.matches(selector)) matches.push(node);
    if (typeof node.querySelectorAll === "function") {
      matches.push(...node.querySelectorAll(selector));
    }
    return matches;
  }

  function prepareScrollScenes(node = document) {
    matchingElements(node, SCROLL_SCENE_SELECTOR).forEach(scene => {
      scene.classList.add("toki-scroll-scene");
      if (scene.matches(".hero-opening, .services-section, .policy-hero, .admin-main, .client-main")) {
        scene.classList.add("toki-scroll-scene--dark");
      }
      const hasTrack = Array.from(scene.children).some(child => child.classList.contains("toki-scene-track"));
      if (!hasTrack) {
        const track = document.createElement("span");
        track.className = "toki-scene-track";
        track.setAttribute("aria-hidden", "true");
        scene.prepend(track);
      }
    });

    matchingElements(node, SCROLL_PARALLAX_SELECTOR).forEach(media => {
      media.classList.add("toki-scroll-parallax");
    });
    refreshScrollTargets();
  }

  function prepare(element) {
    if (!(element instanceof HTMLElement)) return;
    if (element.matches(".hero-opening, .toki-scene-track")) return;

    const hasRevealAttr = element.hasAttribute("data-reveal");
    if (!hasRevealAttr && !element.classList.contains("motion-item")) {
      element.classList.add("motion-item");
      const siblings = element.parentElement
        ? Array.from(element.parentElement.children).filter(child => child.matches(ALL_SELECTOR))
        : [];
      const index = Math.max(0, siblings.indexOf(element));
      element.style.setProperty("--motion-delay", Math.min(index, 7) * 62 + "ms");
    }

    if (!element.dataset.motion) {
      element.dataset.motion = resolveProfile(element);
    }

    if (reduced || !observer) {
      markVisible(element);
    } else {
      observer.observe(element);
    }
  }

  function scan(node = document) {
    if (!node) return;
    prepareScrollScenes(node);
    if (node instanceof HTMLElement) {
      if (node.matches(ALL_SELECTOR) || node.hasAttribute("data-reveal")) prepare(node);
    }
    if (typeof node.querySelectorAll === "function") {
      node.querySelectorAll(`${ALL_SELECTOR}, [data-reveal]`).forEach(prepare);
    }
  }

  function createObserver() {
    if (reduced || !("IntersectionObserver" in window)) return null;
    return new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) markVisible(entry.target);
        else markHidden(entry.target);
      });
    }, {
      threshold: 0.04,
      rootMargin: "0px 0px -3% 0px"
    });
  }

  observer = createObserver();

  /* Interactive pointer parallax & 3D tilt for optical cards. */
  const interactiveCards = ".toki-card, .package-card, .gallery-card, .process-step, .calculator-wrap, .toki-pillar, .album-card";
  let activeTiltCard = null;
  if (fineHover.matches) {
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

  /* Trigger optical shutter flash on major studio CTAs. */
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

  /* Continuous scroll-linked optical depth, exposure meter angle, and damped velocity. */
  let scrollFrame = 0;
  let decayFrame = 0;
  let prevScrollY = window.scrollY || 0;
  let smoothedVel = 0;

  function updateSectionDepth(vh) {
    const scenes = scrollScenes;
    let focusedScene = null;
    let focusedScore = -1;

    scenes.forEach(scene => {
      const rect = scene.getBoundingClientRect();
      const centerOffset = ((rect.top + rect.height * 0.5) - vh * 0.5) / Math.max(1, vh);
      const clamped = Math.max(-1, Math.min(1, centerOffset));
      const progress = Math.min(1, Math.max(0, (vh - rect.top) / Math.max(1, vh + rect.height)));
      const focus = Math.max(0, Math.min(1, 1 - Math.abs(clamped)));

      scene.style.setProperty("--toki-scene-progress", progress.toFixed(4));
      scene.style.setProperty("--toki-scene-position", (progress * 100).toFixed(2) + "%");
      scene.style.setProperty("--toki-scene-opacity", (0.42 + focus * 0.58).toFixed(3));
      scene.style.setProperty("--toki-scene-focus", focus.toFixed(3));

      const intersectsFocusBand = rect.bottom > vh * 0.18 && rect.top < vh * 0.82;
      if (intersectsFocusBand && focus > focusedScore) {
        focusedScene = scene;
        focusedScore = focus;
      }
    });

    /* Keep one clear focal chapter at a time, even when sections overlap. */
    scenes.forEach(scene => {
      scene.classList.toggle("is-scene-active", scene === focusedScene);
    });

    scrollTracked.forEach(el => {
      const rect = el.getBoundingClientRect();
      if (rect.bottom < -120 || rect.top > vh + 120) return;
      const centerOffset = ((rect.top + rect.height * 0.5) - vh * 0.5) / Math.max(1, vh);
      const clamped = Math.max(-1, Math.min(1, centerOffset));
      el.style.setProperty("--el-center", clamped.toFixed(3));
    });

    const parallaxStrength = root.dataset.motionTier === "lite"
      ? 6
      : root.dataset.viewportClass === "phone" ? 9 : 16;
    scrollParallax.forEach(media => {
      const rect = media.getBoundingClientRect();
      if (rect.bottom < -120 || rect.top > vh + 120) return;
      const centerOffset = ((rect.top + rect.height * 0.5) - vh * 0.5) / Math.max(1, vh);
      const clamped = Math.max(-1, Math.min(1, centerOffset));
      media.style.setProperty("--toki-parallax-y", (-clamped * parallaxStrength).toFixed(1) + "px");
    });
  }
  function stepScrollMetrics() {
    scrollFrame = 0;
    if (reduced) return;
    const sy = window.scrollY || 0;
    const vh = Math.max(1, window.innerHeight || 1);
    const maxScroll = Math.max(1, root.scrollHeight - vh);
    const pct = Math.min(1, Math.max(0, sy / maxScroll));
    const deg = (pct * 360).toFixed(1) + "deg";
    const delta = sy - prevScrollY;
    if (delta !== 0) root.dataset.scrollDirection = delta > 0 ? "down" : "up";
    prevScrollY = sy;

    const instantVel = Math.max(-1, Math.min(1, delta / 48));
    smoothedVel = smoothedVel * 0.55 + instantVel * 0.45;

    root.style.setProperty("--scroll-y", sy.toFixed(1));
    root.style.setProperty("--scroll-pct", pct.toFixed(4));
    root.style.setProperty("--scroll-deg", deg);
    root.style.setProperty("--scroll-vel", smoothedVel.toFixed(3));

    updateSectionDepth(vh);

    if (Math.abs(smoothedVel) > 0.012 && !decayFrame) {
      decayFrame = requestAnimationFrame(decayVelocity);
    }
  }

  function decayVelocity() {
    decayFrame = 0;
    if (reduced) return;
    smoothedVel *= 0.84;
    if (Math.abs(smoothedVel) < 0.012) {
      smoothedVel = 0;
      root.style.setProperty("--scroll-vel", "0");
      return;
    }
    root.style.setProperty("--scroll-vel", smoothedVel.toFixed(3));
    decayFrame = requestAnimationFrame(decayVelocity);
  }


  /* Unified masthead visibility: scroll-direction aware and locked while the homepage hero is visible. */
  const headerElements = Array.from(document.querySelectorAll(".site-header, .admin-header, .client-header"));
  const headerHero = document.querySelector(".hero-opening");
  const headerNavigation = document.querySelector(".primary-nav");
  let headerPreviousY = Math.max(0, window.scrollY || 0);
  let headerDirection = 0;
  let headerDirectionDistance = 0;
  let headerFrame = 0;
  const HEADER_DIRECTION_THRESHOLD = 3;

  function heroOwnsViewport() {
    if (!headerHero) return false;
    const bounds = headerHero.getBoundingClientRect();
    return bounds.bottom > 1 && bounds.top < Math.max(1, window.innerHeight || 1);
  }

  function setHeaderVisible(visible) {
    if (!headerElements.length) return false;
    const heroLock = heroOwnsViewport();
    const navigationOpen = Boolean(headerNavigation?.classList.contains("is-open"));
    const focusWithinHeader = headerElements.some(header => header.matches(":focus-within"));
    const shouldShow = navigationOpen || focusWithinHeader || (Boolean(visible) && !heroLock);
    headerElements.forEach(header => {
      header.classList.toggle("is-auto-hidden", !shouldShow);
      if (heroLock && header.classList.contains("site-header")) header.classList.add("is-initial-hidden");
      else header.classList.remove("is-initial-hidden");
      header.setAttribute("aria-hidden", String(!shouldShow));
      if ("inert" in header) header.inert = !shouldShow;
    });
    return shouldShow;
  }

  function updateHeaderVisibility() {
    const currentY = Math.max(0, window.scrollY || 0);
    const delta = currentY - headerPreviousY;
    const heroLock = heroOwnsViewport();
    const focusWithinHeader = headerElements.some(header => header.matches(":focus-within"));
    const navigationOpen = Boolean(headerNavigation?.classList.contains("is-open"));

    if (navigationOpen || focusWithinHeader) {
      headerDirection = 0;
      headerDirectionDistance = 0;
      setHeaderVisible(true);
    } else if (heroLock) {
      headerDirection = 0;
      headerDirectionDistance = 0;
      setHeaderVisible(false);
    } else if (currentY <= 1) {
      headerDirection = 0;
      headerDirectionDistance = 0;
      setHeaderVisible(true);
    } else if (Math.abs(delta) > 0) {
      const nextDirection = Math.sign(delta);
      if (nextDirection !== headerDirection) {
        headerDirection = nextDirection;
        headerDirectionDistance = 0;
      }
      headerDirectionDistance += Math.abs(delta);
      if (headerDirectionDistance >= HEADER_DIRECTION_THRESHOLD) {
        setHeaderVisible(headerDirection < 0);
        headerDirectionDistance = 0;
      }
    }
    headerPreviousY = currentY;
  }

  if (headerElements.length) {
    setHeaderVisible(window.scrollY <= 1 && !heroOwnsViewport());
    updateHeaderVisibility();
    window.addEventListener("scroll", () => {
      const currentY = Math.max(0, window.scrollY || 0);
      // Restore the masthead synchronously at the document top. This keeps the
      // header's visible, aria, and inert states aligned before the next paint.
      // The homepage hero retains ownership of the viewport and stays locked.
      if (currentY <= 1 && !heroOwnsViewport()) {
        headerDirection = 0;
        headerDirectionDistance = 0;
        headerPreviousY = currentY;
        setHeaderVisible(true);
      } else if (currentY < headerPreviousY && !heroOwnsViewport()) {
        // Reveal on the first upward movement instead of waiting for the
        // animation-frame callback. This keeps the masthead responsive even
        // when a page is under browser load or scroll updates are coalesced.
        headerDirection = -1;
        headerDirectionDistance = 0;
        headerPreviousY = currentY;
        setHeaderVisible(true);
      }
      if (headerFrame) return;
      headerFrame = requestAnimationFrame(() => {
        headerFrame = 0;
        updateHeaderVisibility();
      });
    }, { passive: true });
    // Programmatic smooth-scroll and touch momentum can deliver their final
    // position after the last directional frame. Reconcile the masthead once
    // scrolling settles so visual and accessibility states cannot remain stale.
    window.addEventListener("scrollend", () => {
      const currentY = Math.max(0, window.scrollY || 0);
      if (currentY <= 1 && !heroOwnsViewport()) {
        headerDirection = 0;
        headerDirectionDistance = 0;
        headerPreviousY = currentY;
        setHeaderVisible(true);
      } else {
        updateHeaderVisibility();
      }
    }, { passive: true });
    window.addEventListener("resize", updateHeaderVisibility, { passive: true });
    window.addEventListener("orientationchange", () => requestAnimationFrame(updateHeaderVisibility), { passive: true });
  }

  const coarsePointer = window.matchMedia("(pointer: coarse)");

  function computeMotionTier() {
    if (reduced) return "reduced";
    const conn = navigator.connection;
    const saveData = Boolean(conn?.saveData);
    const slowNet = conn?.effectiveType === "2g" || conn?.effectiveType === "slow-2g";
    const lowCores = typeof navigator.hardwareConcurrency === "number" && navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 2;
    return saveData || slowNet || lowCores ? "lite" : "full";
  }

  function syncAdaptiveEnvironment() {
    const w = Math.max(1, window.innerWidth || root.clientWidth || 1024);
    const viewportHeight = Math.max(1, window.innerHeight || root.clientHeight || 1);
    root.style.setProperty("--toki-viewport-height", viewportHeight + "px");
    const viewportClass = w <= 680 ? "phone" : w <= 1180 ? "tablet" : w >= 1800 ? "tv" : "desktop";
    root.dataset.viewportClass = viewportClass;
    root.dataset.pointerMode = coarsePointer.matches ? "coarse" : "fine";
    root.dataset.motionTier = computeMotionTier();
  }
  syncAdaptiveEnvironment();
  coarsePointer.addEventListener?.("change", syncAdaptiveEnvironment);
  navigator.connection?.addEventListener?.("change", syncAdaptiveEnvironment);

  window.addEventListener("scroll", () => {
    if (!scrollFrame && !reduced) scrollFrame = requestAnimationFrame(stepScrollMetrics);
  }, { passive: true });
  window.addEventListener("resize", () => {
    syncAdaptiveEnvironment();
    if (!scrollFrame && !reduced) scrollFrame = requestAnimationFrame(stepScrollMetrics);
  }, { passive: true });
  window.addEventListener("orientationchange", syncAdaptiveEnvironment, { passive: true });
  scan(document);
  stepScrollMetrics();

  if ("MutationObserver" in window) {
    mutationObserver = new MutationObserver(records => {
      records.forEach(record => {
        record.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) scan(node);
        });
      });
      refreshScrollTargets();
    });
    mutationObserver.observe(document.body, { childList: true, subtree: true });
  }

  preference.addEventListener?.("change", event => {
    reduced = event.matches;
    syncAdaptiveEnvironment();
    if (reduced) {
      observer?.disconnect();
      observer = null;
      document.querySelectorAll(".motion-item, [data-reveal]").forEach(element => {
        markVisible(element);
        element.style.removeProperty("--motion-delay");
      });
      root.style.removeProperty("--scroll-y");
      root.style.removeProperty("--scroll-pct");
      root.style.removeProperty("--scroll-deg");
      root.style.removeProperty("--scroll-vel");
      root.removeAttribute("data-scroll-direction");
      document.querySelectorAll(".toki-scroll-scene").forEach(scene => {
        scene.classList.remove("is-scene-active");
        scene.style.removeProperty("--toki-scene-progress");
        scene.style.removeProperty("--toki-scene-position");
        scene.style.removeProperty("--toki-scene-opacity");
        scene.style.removeProperty("--toki-scene-focus");
      });
      document.querySelectorAll(".toki-scroll-parallax").forEach(media => {
        media.style.removeProperty("--toki-parallax-y");
      });
    } else {
      observer = createObserver();
      if (observer) {
        document.querySelectorAll(".motion-item, [data-reveal]").forEach(element => {
          observer.observe(element);
        });
      }
      scan(document);
      stepScrollMetrics();
    }
  });

  window.addEventListener("pagehide", () => {
    observer?.disconnect();
    mutationObserver?.disconnect();
    if (scrollFrame) cancelAnimationFrame(scrollFrame);
    if (decayFrame) cancelAnimationFrame(decayFrame);
  }, { once: true });

  window.TokiMotion = Object.freeze({
    animate,
    animateOut,
    animateBackdropOut,
    swap,
    updateText,
    setMenuOpen,
    setHeaderVisible,
    closeDialog,
    triggerShutterFlash,
    pulseMetric,
    rescan: scan,
    refreshScrollScenes(node = document) {
      scan(node);
      if (!reduced) stepScrollMetrics();
    },
    get reduced() { return reduced; }
  });
})();
