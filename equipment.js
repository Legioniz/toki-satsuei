(() => {
  "use strict";

  const root = document.querySelector("[data-equipment-root]");
  if (!root) return;

  const stage = root.querySelector("[data-equipment-stage]");
  const model = root.querySelector("[data-camera-object]");
  const modelRegion = root.querySelector("[data-camera-model]");
  const blueprint = root.querySelector("[data-equipment-blueprint]");
  const status = root.querySelector("[data-equipment-status]");
  const modeButtons = Array.from(root.querySelectorAll("[data-equipment-mode]"));
  const componentButtons = Array.from(root.querySelectorAll("[data-equipment-component]"));
  const blueprintButtons = Array.from(root.querySelectorAll("[data-blueprint-view]"));
  const blueprintPanels = Array.from(root.querySelectorAll("[data-blueprint-panel]"));
  const specPanels = Array.from(root.querySelectorAll("[data-spec-panel]"));
  const controls = root.querySelector("[data-equipment-rotation-controls]");
  const rotateLeft = root.querySelector("[data-rotate-left]");
  const rotateRight = root.querySelector("[data-rotate-right]");
  const rotateUp = root.querySelector("[data-rotate-up]");
  const rotateDown = root.querySelector("[data-rotate-down]");
  const reset = root.querySelector("[data-rotate-reset]");

  if (!stage || !model || !modelRegion || !blueprint || !status) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const initialRotation = { x: -12, y: -28 };
  let rotation = { ...initialRotation };
  let drag = null;
  let frame = 0;
  let pendingRotation = null;

  function renderRotation() {
    if (!pendingRotation) return;
    const next = pendingRotation;
    pendingRotation = null;
    model.style.setProperty("--camera-rx", next.x + "deg");
    model.style.setProperty("--camera-ry", next.y + "deg");
    model.classList.toggle("is-dragging", Boolean(drag));
    frame = 0;
  }

  function setRotation(x, y) {
    rotation = {
      x: Math.max(-34, Math.min(34, x)),
      y: ((y + 180) % 360 + 360) % 360 - 180
    };
    pendingRotation = rotation;
    if (!frame) frame = window.requestAnimationFrame(renderRotation);
  }

  function announce(message) {
    status.textContent = message;
  }

  function setMode(mode) {
    const next = mode === "2d" ? "2d" : "3d";
    stage.dataset.view = next;
    blueprint.hidden = next !== "2d";
    modeButtons.forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.equipmentMode === next));
    });
    const blueprintViewControls = root.querySelector("[data-blueprint-view-controls]");
    if (blueprintViewControls) blueprintViewControls.hidden = next !== "2d";
    if (controls) controls.hidden = next !== "3d";
    announce(next === "3d" ? "3D INTERACTIVE VIEW" : "2D ORTHOGRAPHIC VIEW");
  }

  function setComponent(component) {
    const next = component === "lens" ? "lens" : "camera";
    root.dataset.equipmentFocus = next;
    modelRegion.dataset.focus = next;
    model.dataset.focus = next;
    blueprint.dataset.focus = next;
    componentButtons.forEach(button => {
      const active = button.dataset.equipmentComponent === next;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    specPanels.forEach(panel => {
      panel.hidden = panel.dataset.specPanel !== next;
    });
    announce(next === "lens" ? "LENS SELECTED — 18 TO 55 MILLIMETRES" : "CAMERA BODY SELECTED — EOS 3000D");
  }

  function setBlueprintView(view) {
    const next = ["front", "rear", "side"].includes(view) ? view : "front";
    blueprint.dataset.view = next;
    blueprintPanels.forEach(panel => {
      panel.hidden = panel.dataset.blueprintPanel !== next;
    });
    blueprintButtons.forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.blueprintView === next));
    });
    announce(next.toUpperCase() + " 2D SCHEMATIC");
  }

  modeButtons.forEach(button => {
    button.addEventListener("click", () => setMode(button.dataset.equipmentMode));
  });
  componentButtons.forEach(button => {
    button.addEventListener("click", () => setComponent(button.dataset.equipmentComponent));
    button.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const next = button.dataset.equipmentComponent === "camera" ? "lens" : "camera";
      root.querySelector('[data-equipment-component="' + next + '"]')?.focus();
      setComponent(next);
    });
  });
  blueprintButtons.forEach(button => {
    button.addEventListener("click", () => setBlueprintView(button.dataset.blueprintView));
  });

  rotateLeft?.addEventListener("click", () => setRotation(rotation.x, rotation.y - 18));
  rotateRight?.addEventListener("click", () => setRotation(rotation.x, rotation.y + 18));
  rotateUp?.addEventListener("click", () => setRotation(rotation.x - 10, rotation.y));
  rotateDown?.addEventListener("click", () => setRotation(rotation.x + 10, rotation.y));
  reset?.addEventListener("click", () => setRotation(initialRotation.x, initialRotation.y));

  modelRegion.addEventListener("keydown", event => {
    const step = event.shiftKey ? 24 : 12;
    if (event.key === "ArrowLeft") setRotation(rotation.x, rotation.y - step);
    else if (event.key === "ArrowRight") setRotation(rotation.x, rotation.y + step);
    else if (event.key === "ArrowUp") setRotation(rotation.x - step, rotation.y);
    else if (event.key === "ArrowDown") setRotation(rotation.x + step, rotation.y);
    else if (event.key === "Home") setRotation(initialRotation.x, initialRotation.y);
    else return;
    event.preventDefault();
  });

  modelRegion.addEventListener("pointerdown", event => {
    if (event.pointerType !== "mouse" || reducedMotion.matches || stage.dataset.view !== "3d") return;
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY, rotationX: rotation.x, rotationY: rotation.y };
    modelRegion.setPointerCapture?.(event.pointerId);
    model.classList.add("is-dragging");
  });
  modelRegion.addEventListener("pointermove", event => {
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    setRotation(drag.rotationX - dy * 0.42, drag.rotationY + dx * 0.52);
  });
  function endDrag(event) {
    if (!drag || (event && drag.id !== event.pointerId)) return;
    drag = null;
    model.classList.remove("is-dragging");
  }
  modelRegion.addEventListener("pointerup", endDrag);
  modelRegion.addEventListener("pointercancel", endDrag);
  modelRegion.addEventListener("lostpointercapture", endDrag);

  setBlueprintView("front");
  setComponent("camera");
  setMode("3d");
  root.dataset.equipmentReady = "true";
})();