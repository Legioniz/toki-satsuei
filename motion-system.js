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
    ".announcement",
    ".site-header .brand",
    ".site-header .primary-nav > a",
    ".intro-inner > *",
    ".section-heading > div > .eyebrow",
    ".section-heading > div > h2",
    ".section-heading > .section-aside",
    ".work-filters > *",
    ".gallery-card",
    ".gallery-footnote",
    ".facebook-feed-intro > *",
    ".facebook-feed-toolbar",
    ".facebook-feed-tools",
    ".facebook-feed-filter",
    ".facebook-feed-state",
    ".facebook-embed-card",
    ".service-row h3",
    ".service-row p",
    ".service-row .service-arrow",
    ".package-card .package-art > *",
    ".package-card .package-top > *",
    ".package-card h3",
    ".package-card .package-price",
    ".package-card ul",
    ".package-card .package-link",
    ".service-row .service-number",
    ".session-notes > *",
    ".session-notes > div > small",
    ".session-notes > div > p",
    ".about-copy > .eyebrow",
    ".about-copy > h2",
    ".about-copy > p",
    ".about-copy .about-signature",
    ".contact-copy > .eyebrow",
    ".contact-copy > h2",
    ".contact-copy > p",
    ".contact-copy > a",
    ".contact-copy > .contact-small",
    ".inquiry-form > label",
    ".inquiry-form > .form-split",
    ".inquiry-form > .form-submit",
    ".library-page .library-hero > *",
    ".library-page .library-toolbar > *",
    ".library-page .library-filter",
    ".library-page .archive-search",
    ".library-page .rail-button",
    ".library-page .archive-group-head",
    ".library-page .archive-rail-top",
    ".library-page .album-card",
    ".library-page .archive-empty > *",
    ".album-dialog-head > *",
    ".album-frame",
    ".footer-main > *",
    ".footer-bottom > *",
    ".footer-socials > *"
  ].join(",");

  root.classList.add("motion-system-ready");

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

  window.TokiMotion = Object.freeze({
    animate,
    animateOut,
    animateBackdropOut,
    swap,
    updateText,
    setMenuOpen,
    closeDialog,
    get reduced() { return reduced; }
  });

  function reveal(element) {
    element.classList.add("is-motion-visible");
    if (observer) observer.unobserve(element);
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
    element.style.setProperty("--motion-delay", Math.min(index, 5) * 48 + "ms");

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
        if (entry.isIntersecting) reveal(entry.target);
      });
    }, {
      threshold: 0.08,
      rootMargin: "0px 0px -7% 0px"
    });
  }

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
