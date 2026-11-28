(() => {
  "use strict";

  const root = document.querySelector("[data-equipment-root]");
  if (!root || root.dataset.equipmentReady === "true") return;

  const stage = root.querySelector("[data-equipment-stage]");
  const photo = root.querySelector("[data-equipment-photo]");
  const embedHost = root.querySelector("[data-equipment-embed]");
  const status = root.querySelector("[data-equipment-status]");
  const modeButtons = Array.from(root.querySelectorAll("[data-equipment-mode]"));
  const angleButtons = Array.from(root.querySelectorAll("[data-equipment-angle]"));
  const angleControls = root.querySelector("[data-equipment-angles]");
  const modelUid = "7d57163f3bec464cbb213428e1c37cf7";
  const viewerApiSource = "https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js";
  const angles = {
    front: { src: "./assets/equipment/camera/EOS-3000D-front.png", label: "Front view of the submitted Canon EOS 3000D camera with an EF-S 18–55mm kit lens." },
    flash: { src: "./assets/equipment/camera/EOS-3000D-pop-up-flash.png", label: "Front view of the submitted Canon EOS 3000D with its pop-up flash raised." },
    left: { src: "./assets/equipment/camera/EOS-3000D-left-side.png", label: "Left-side profile of the submitted EOS 3000D showing the side port covers and attached lens." },
    right: { src: "./assets/equipment/camera/EOS-3000D-right-side.png", label: "Right-side profile of the submitted EOS 3000D with the attached lens." },
    top: { src: "./assets/equipment/camera/EOS-3000D-top.png", label: "Top view of the submitted Canon EOS 3000D and attached EF-S 18–55mm kit lens." }
  };

  if (!stage || !photo || !embedHost || !status || !modeButtons.length || !angleButtons.length) return;

  let iframe = null;
  let viewerApiPromise = null;
  let viewerStarted = false;

  function announce(message) {
    status.textContent = message;
  }

  function setAngle(name) {
    const selected = angles[name] ? name : "front";
    const angle = angles[selected];
    photo.dataset.angle = selected;
    photo.src = angle.src;
    photo.alt = angle.label;
    angleButtons.forEach(button => {
      const active = button.dataset.equipmentAngle === selected;
      button.setAttribute("aria-pressed", String(active));
    });
    announce("2D PHOTO VIEW / " + selected.toUpperCase());
  }

  function loadViewerApi() {
    if (typeof window.Sketchfab === "function") return Promise.resolve(window.Sketchfab);
    if (viewerApiPromise) return viewerApiPromise;

    viewerApiPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector("script[data-sketchfab-viewer-api]");
      const script = existing || document.createElement("script");
      const onLoad = () => {
        if (typeof window.Sketchfab === "function") resolve(window.Sketchfab);
        else reject(new Error("Sketchfab Viewer API did not initialize."));
      };
      const onError = () => reject(new Error("Sketchfab Viewer API could not be loaded."));

      if (existing) {
        existing.addEventListener("load", onLoad, { once: true });
        existing.addEventListener("error", onError, { once: true });
        return;
      }

      script.src = viewerApiSource;
      script.async = true;
      script.dataset.sketchfabViewerApi = "true";
      script.addEventListener("load", onLoad, { once: true });
      script.addEventListener("error", onError, { once: true });
      document.head.appendChild(script);
    });

    return viewerApiPromise;
  }

  function requestHighDefinitionTextures(api) {
    api.addEventListener("viewerready", () => {
      if (typeof api.setTextureQuality !== "function") {
        announce("3D MODEL / HD TEXTURE CONTROL UNAVAILABLE");
        return;
      }

      api.setTextureQuality("hd", error => {
        announce(error
          ? "3D MODEL / HD TEXTURE REQUEST FAILED: DEFAULT QUALITY"
          : "3D MODEL / HIGH-DEFINITION TEXTURES REQUESTED");
      });
    });
  }

  function startViewer() {
    if (!iframe || viewerStarted) return;
    viewerStarted = true;
    announce("3D MODEL / LOADING VIEWER API");

    loadViewerApi().then(Sketchfab => {
      if (!iframe || !embedHost.contains(iframe)) return;
      const client = new Sketchfab(iframe);

      client.init(modelUid, {
        autostart: 1,
        success: api => {
          api.start(() => requestHighDefinitionTextures(api));
        },
        error: () => {
          viewerStarted = false;
          announce("3D MODEL / VIEWER FAILED: RETRY BY RESELECTING 3D");
        }
      });
    }).catch(() => {
      viewerStarted = false;
      announce("3D MODEL / VIEWER API UNAVAILABLE");
    });
  }

  function ensureViewer() {
    if (iframe) {
      startViewer();
      return;
    }

    iframe = document.createElement("iframe");
    iframe.title = "Interactive Sketchfab 3D reference model titled Canon EOS 3000";
    iframe.loading = "lazy";
    iframe.allow = "autoplay; fullscreen; xr-spatial-tracking";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.setAttribute("aria-label", "Interactive 3D Canon EOS 3000 reference model hosted by Sketchfab");
    embedHost.appendChild(iframe);
    startViewer();
  }

  function setMode(mode) {
    const selected = mode === "3d" ? "3d" : "2d";
    stage.dataset.view = selected;
    const show3d = selected === "3d";
    embedHost.hidden = !show3d;
    angleControls.hidden = show3d;
    if (show3d) {
      ensureViewer();
    } else {
      setAngle(photo.dataset.angle || "front");
    }
    modeButtons.forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.equipmentMode === selected));
    });
  }

  modeButtons.forEach(button => {
    button.addEventListener("click", () => setMode(button.dataset.equipmentMode));
  });
  angleButtons.forEach(button => {
    button.addEventListener("click", () => setAngle(button.dataset.equipmentAngle));
  });

  root.dataset.equipmentReady = "true";
  setAngle("front");
  setMode("2d");
})();
