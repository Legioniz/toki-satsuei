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
    ".section-heading > *",
    ".work-filters > *",
    ".gallery-card",
    ".gallery-footnote",
    ".facebook-feed-intro > *",
    ".facebook-feed-toolbar",
    ".facebook-feed-tools",
    ".facebook-embed-card",
    ".service-row",
    ".session-notes > *",
    ".library-page .library-hero > *",
    ".library-page .library-toolbar > *",
    ".library-page .archive-rail-top",
    ".library-page .album-card",
    ".library-page .archive-empty > *",
    ".footer-main > *",
    ".footer-bottom > *",
    ".footer-socials > *"
  ].join(",");

  root.classList.add("motion-system-ready");

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
      if (mutationObserver) scan(document);
    }
  });

  window.addEventListener("pagehide", () => {
    observer?.disconnect();
    mutationObserver?.disconnect();
  }, { once: true });
})();
