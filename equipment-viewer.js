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
  const modelEmbed = "https://sketchfab.com/models/7d57163f3bec464cbb213428e1c37cf7/embed";
  const angles = {
    front: { position: "0%", label: "Front view of a Canon EOS 3000D camera with an EF-S 18–55mm kit lens." },
    flash: { position: "25%", label: "Front view of the Canon EOS 3000D with its pop-up flash raised." },
    left: { position: "50%", label: "Left-side profile of the Canon EOS 3000D showing the side port covers and attached lens." },
    right: { position: "75%", label: "Right-side profile of the Canon EOS 3000D with the attached lens." },
    top: { position: "100%", label: "Top view of the Canon EOS 3000D and attached EF-S 18–55mm kit lens." }
  };

  if (!stage || !photo || !embedHost || !status || !modeButtons.length || !angleButtons.length) return;

  let iframe = null;

  function announce(message) {
    status.textContent = message;
  }

  function setAngle(name) {
    const selected = angles[name] ? name : "front";
    const angle = angles[selected];
    photo.dataset.angle = selected;
    photo.style.backgroundPosition = angle.position + " 50%";
    photo.setAttribute("aria-label", angle.label);
    angleButtons.forEach(button => {
      const active = button.dataset.equipmentAngle === selected;
      button.setAttribute("aria-pressed", String(active));
    });
    announce("2D PHOTO VIEW / " + selected.toUpperCase());
  }

  function ensureViewer() {
    if (iframe) return;
    iframe = document.createElement("iframe");
    iframe.title = "Interactive Sketchfab 3D reference model titled Canon EOS 3000";
    iframe.src = modelEmbed;
    iframe.loading = "lazy";
    iframe.allow = "autoplay; fullscreen; xr-spatial-tracking";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.setAttribute("aria-label", "Interactive 3D Canon EOS 3000 reference model hosted by Sketchfab");
    embedHost.appendChild(iframe);
  }

  function setMode(mode) {
    const selected = mode === "3d" ? "3d" : "2d";
    stage.dataset.view = selected;
    const show3d = selected === "3d";
    embedHost.hidden = !show3d;
    angleControls.hidden = show3d;
    if (show3d) {
      ensureViewer();
      announce("3D MODEL / SKETCHFAB COMMUNITY REFERENCE");
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
