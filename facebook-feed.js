(function () {
  "use strict";

  const list = document.querySelector("#facebook-feed-list");
  const status = document.querySelector("#facebook-feed-status");
  const search = document.querySelector("#facebook-feed-search");
  const filters = document.querySelector("#facebook-feed-filters");
  const tools = document.querySelector(".facebook-feed-tools");
  const scrollControls = document.querySelector("#facebook-feed-scroll-controls");
  const previous = document.querySelector("#facebook-feed-previous");
  const next = document.querySelector("#facebook-feed-next");

  if (!list || !status) return;

  const PAGE = "https://www.facebook.com/tokisatsuiephotography/";
  const CATEGORIES = {
    cosplay: "Cosplay",
    events: "Events",
    announcements: "Announcements",
    "behind-the-scenes": "Behind the scenes",
    community: "Community",
    other: "Other"
  };

  let posts = [];
  let activeCategory = "all";
  let searchTerm = "";
  let sdkPromise = null;

  function node(tag, className, content) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined) element.textContent = String(content);
    return element;
  }

  function normalizeFacebookUrl(value) {
    try {
      const url = new URL(String(value || "").trim());
      const path = url.pathname.toLowerCase();
      const hosts = ["facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com"];
      const supportedPath = /\/(posts|permalink|videos|reel|photo|watch|share\/p|share\/r)(\/|$)/.test(path)
        || path.endsWith("/photo.php")
        || url.searchParams.has("story_fbid")
        || url.searchParams.has("fbid")
        || url.searchParams.has("v");

      if (url.protocol !== "https:" || !hosts.includes(url.hostname.toLowerCase()) || !supportedPath) return "";
      url.hash = "";
      return url.href;
    } catch (error) {
      return "";
    }
  }

  function categoryLabel(value) {
    return CATEGORIES[value] || "Other";
  }

  function visiblePosts() {
    return posts.filter(post => {
      const matchesCategory = activeCategory === "all" || post.category === activeCategory;
      const searchable = (post.label + " " + categoryLabel(post.category) + " " + post.url).toLowerCase();
      return matchesCategory && (!searchTerm || searchable.includes(searchTerm));
    });
  }

  function syncScrollControls() {
    const cardCount = list.querySelectorAll(".facebook-embed-card").length;
    const maxScroll = Math.max(0, list.scrollWidth - list.clientWidth);
    const canScroll = cardCount > 1 && maxScroll > 2;

    if (scrollControls) scrollControls.hidden = !canScroll;
    if (previous) previous.disabled = !canScroll || list.scrollLeft <= 2;
    if (next) next.disabled = !canScroll || list.scrollLeft >= maxScroll - 2;
  }

  function scrollPosts(direction) {
    const firstCard = list.querySelector(".facebook-embed-card");
    if (!firstCard) return;

    const gap = parseFloat(window.getComputedStyle(list).gap) || 14;
    const step = Math.min(list.clientWidth, firstCard.getBoundingClientRect().width + gap);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    list.scrollBy({ left: direction * Math.max(step, 120), behavior: reducedMotion ? "auto" : "smooth" });
  }

  function loadFacebookSdk() {
    if (window.FB && window.FB.XFBML) return Promise.resolve(window.FB);
    if (sdkPromise) return sdkPromise;

    sdkPromise = new Promise((resolve, reject) => {
      let script = document.getElementById("facebook-jssdk");
      if (!script) {
        script = document.createElement("script");
        script.id = "facebook-jssdk";
        script.async = true;
        script.defer = true;
        script.crossOrigin = "anonymous";
        script.src = "https://connect.facebook.net/en_US/sdk.js#xfbml=0&version=v27.0";
        document.head.append(script);
      }
      script.addEventListener("load", () => {
        if (window.FB && window.FB.XFBML) resolve(window.FB);
        else reject(new Error("Facebook SDK unavailable"));
      }, { once: true });
      script.addEventListener("error", () => reject(new Error("Facebook SDK blocked")), { once: true });
    });

    return sdkPromise;
  }

  function showEmptyState(title, description) {
    const box = node("div", "facebook-feed-state");
    box.append(node("span", "facebook-state-mark", "時"));
    box.append(node("strong", "", title));
    box.append(node("p", "", description));

    const link = node("a", "facebook-state-link", "OPEN FACEBOOK PAGE ↗");
    link.href = PAGE;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    box.append(link);

    list.replaceChildren(box);
    list.setAttribute("aria-busy", "false");
    syncScrollControls();
  }

  function drawFilters() {
    if (!filters) return;

    filters.replaceChildren();
    const counts = { all: posts.length };
    posts.forEach(post => {
      counts[post.category] = (counts[post.category] || 0) + 1;
    });

    ["all"].concat(Object.keys(CATEGORIES).filter(key => counts[key])).forEach(key => {
      const label = key === "all" ? "All" : categoryLabel(key);
      const button = node("button", "facebook-feed-filter" + (activeCategory === key ? " is-active" : ""), label + " · " + counts[key]);
      button.type = "button";
      button.setAttribute("aria-pressed", String(activeCategory === key));
      button.addEventListener("click", () => {
        activeCategory = key;
        drawFilters();
        drawPosts();
      });
      filters.append(button);
    });
  }

  function drawPosts() {
    const shown = visiblePosts();
    list.replaceChildren();
    list.scrollTo({ left: 0, behavior: "auto" });

    if (!posts.length) {
      if (tools) tools.hidden = true;
      status.textContent = "THE COLLECTION IS READY TO GROW";
      showEmptyState(
        "A few more moments, kept close.",
        "Our selected Facebook posts will appear here as a scrollable collection. Follow the page to catch the latest updates."
      );
      return;
    }

    if (tools) tools.hidden = false;

    if (!shown.length) {
      status.textContent = "NO POSTS MATCH THIS FILTER";
      showEmptyState("No posts match this view.", "Try another category or a different search term.");
      return;
    }

    status.textContent = "SHOWING " + shown.length + " OF " + posts.length + " POSTS · SCROLL TO EXPLORE";
    list.setAttribute("aria-busy", "true");

    const embeds = [];
    shown.forEach((post, index) => {
      const card = node("article", "facebook-embed-card" + (post.featured ? " is-featured" : ""));
      const heading = node("div", "facebook-embed-heading");
      const number = node("span", "facebook-embed-index", String(index + 1).padStart(2, "0"));
      const metadata = node("div", "facebook-embed-meta");

      metadata.append(node("span", "facebook-embed-label", post.label || "FROM THE TOKI SATSUEI PAGE"));
      metadata.append(node("span", "facebook-embed-category", categoryLabel(post.category)));
      if (post.featured) metadata.append(node("span", "facebook-embed-featured", "FEATURED"));

      const open = node("a", "facebook-embed-open", "OPEN POST ↗");
      open.href = post.url;
      open.target = "_blank";
      open.rel = "noopener noreferrer";
      open.referrerPolicy = "no-referrer";

      heading.append(number, metadata, open);

      const embed = node("div", "fb-post");
      embed.setAttribute("data-href", post.url);
      embed.setAttribute("data-show-text", "true");
      embed.setAttribute("data-lazy", "true");

      const note = node("p", "facebook-embed-note", "Loading the original Facebook post…");
      card.append(heading, embed, note);
      list.append(card);
      embeds.push({ embed, note });
    });

    syncScrollControls();
    window.requestAnimationFrame(syncScrollControls);

    loadFacebookSdk().then(FB => {
      if (!window.__tokiFacebookSdkInitialized) {
        FB.init({ xfbml: false, version: "v27.0" });
        window.__tokiFacebookSdkInitialized = true;
      }

      FB.XFBML.parse(list);
      window.setTimeout(() => {
        embeds.forEach(item => {
          if (item.embed.querySelector("iframe")) {
            item.note.textContent = "Embedded directly from Facebook. Use the controls inside the post to react, comment, and share.";
            item.note.classList.add("is-embedded");
          } else {
            item.note.textContent = "Facebook could not display this post here. It may be private, removed, or restricted. Open the original post above.";
            item.note.classList.add("is-unavailable");
          }
        });
        list.setAttribute("aria-busy", "false");
        syncScrollControls();
      }, 7000);
    }).catch(() => {
      embeds.forEach(item => {
        item.note.textContent = "Facebook's embed was blocked or unavailable. Open the original post above.";
        item.note.classList.add("is-unavailable");
      });
      list.setAttribute("aria-busy", "false");
      syncScrollControls();
    });
  }

  if (search) {
    search.addEventListener("input", () => {
      searchTerm = search.value.trim().toLowerCase();
      drawPosts();
    });
  }

  if (previous) previous.addEventListener("click", () => scrollPosts(-1));
  if (next) next.addEventListener("click", () => scrollPosts(1));
  list.addEventListener("scroll", syncScrollControls, { passive: true });
  window.addEventListener("resize", syncScrollControls, { passive: true });

  fetch("./facebook-posts.json?v=" + Date.now(), {
    cache: "no-store",
    headers: { Accept: "application/json" }
  }).then(response => {
    if (!response.ok) throw new Error("Post list unavailable");
    return response.json();
  }).then(data => {
    const seen = new Set();
    posts = (Array.isArray(data.posts) ? data.posts : []).map(raw => {
      if (!raw || typeof raw !== "object") return null;
      const url = normalizeFacebookUrl(raw.url);
      if (!url || seen.has(url)) return null;
      seen.add(url);

      return {
        url,
        label: typeof raw.label === "string" ? raw.label.trim().slice(0, 90) : "",
        category: Object.prototype.hasOwnProperty.call(CATEGORIES, raw.category) ? raw.category : "other",
        featured: raw.featured === true
      };
    }).filter(Boolean).slice(0, 12);

    drawFilters();
    drawPosts();
  }).catch(() => {
    if (tools) tools.hidden = true;
    status.textContent = "POST COLLECTION COULD NOT LOAD";
    showEmptyState("We couldn't load the selected posts.", "Reload the page or open our Facebook Page directly.");
  });

  syncScrollControls();
})();
