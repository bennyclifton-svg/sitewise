/*
 * SITEFORM landing — hero band (Prompt 3).
 * Marquee, textured tower house GLB with shutter animation, detail thumbnail.
 */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

(function () {
  "use strict";

  var CLAY = 0xf2f2ef;
  var ORANGE = 0xf96416;
  var BLACK = 0x0c0c0c;
  var INK_DIM = 0x5a5a56;
  var LINE = 0xABABA6;

  var MODEL_URL = "landing-assets/models/tower-house.glb";

  var hero;
  var stageCanvas;
  var detailCanvas;
  var buildingState = null;
  var detailState = null;
  var rafId = 0;
  var heroVisible = true;
  var reducedMotion =
    window.SiteformDisplay && window.SiteformDisplay.prefersReducedMotion();

  function webglSupported() {
    try {
      var c = document.createElement("canvas");
      return !!(
        window.WebGLRenderingContext &&
        (c.getContext("webgl") || c.getContext("experimental-webgl"))
      );
    } catch (e) {
      return false;
    }
  }

  function initMarquee() {
    var band = document.querySelector(".hero__marquee-band");
    if (!band) return;

    var runs = band.querySelectorAll(".hero__marquee-run");
    for (var i = 0; i < runs.length; i++) {
      runs[i].textContent = "BUILDING TOMORROW";
    }

    if (reducedMotion) {
      band.classList.add("hero__marquee-band--static");
    }
  }

  function clayMaterial(roughness, color) {
    return new THREE.MeshStandardMaterial({
      color: typeof color === "number" ? color : CLAY,
      roughness: typeof roughness === "number" ? roughness : 0.92,
      metalness: 0,
    });
  }

  var clayPalette = {
    Clay_Base: clayMaterial(0.92, CLAY),
    Clay_Panel: clayMaterial(0.94, 0xefefec),
    Clay_Ground: clayMaterial(0.96, 0xe9e9e6),
    Clay_Line: clayMaterial(0.88, LINE),
    Clay_InkDim: clayMaterial(0.9, INK_DIM),
    Clay_Orange: clayMaterial(0.78, ORANGE),
    Clay_Black: clayMaterial(0.85, BLACK),
  };

  function prepareModel(root) {
    root.traverse(function (node) {
      if (!node.isMesh) return;

      node.castShadow = true;
      node.receiveShadow = false;
    });
  }

  function startModelAnimations(model, animations) {
    if (!animations || !animations.length || reducedMotion) {
      return null;
    }

    var mixer = new THREE.AnimationMixer(model);
    for (var i = 0; i < animations.length; i++) {
      var action = mixer.clipAction(animations[i]);
      action.setLoop(THREE.LoopRepeat);
      action.play();
    }

    return mixer;
  }

  function createModelSpinner(canvas, group, options) {
    var rotY = options.baseRotY || 0;
    var rotX = 0;
    var velY = 0;
    var velX = 0;
    var dragging = false;
    var pointerId = null;
    var lastX = 0;
    var lastY = 0;
    var lastTime = 0;
    var dragClass = "hero__stage-canvas--dragging";

    var DRAG_SENS = 0.0055;
    var FLICK_SCALE = 14;
    var FRICTION = 0.93;
    var MIN_VEL = 0.00008;
    var MAX_TILT = 0.32;

    function applyRotation() {
      group.rotation.y = rotY;
      group.rotation.x = Math.max(-MAX_TILT, Math.min(MAX_TILT, rotX));
    }

    function onPointerDown(e) {
      if (e.button !== 0) return;

      dragging = true;
      pointerId = e.pointerId;
      lastX = e.clientX;
      lastY = e.clientY;
      lastTime = performance.now();
      velY = 0;
      velX = 0;
      canvas.setPointerCapture(e.pointerId);
      canvas.classList.add(dragClass);
    }

    function onPointerMove(e) {
      if (!dragging || e.pointerId !== pointerId) return;

      var now = performance.now();
      var dt = Math.max(now - lastTime, 1);
      var dx = e.clientX - lastX;
      var dy = e.clientY - lastY;

      rotY += dx * DRAG_SENS;
      rotX += dy * DRAG_SENS * 0.45;
      velY = (dx / dt) * DRAG_SENS * FLICK_SCALE;
      velX = (dy / dt) * DRAG_SENS * 0.45 * FLICK_SCALE;
      lastX = e.clientX;
      lastY = e.clientY;
      lastTime = now;
      applyRotation();
    }

    function endDrag(e) {
      if (!dragging) return;
      if (e && e.pointerId !== pointerId) return;

      dragging = false;
      pointerId = null;
      canvas.classList.remove(dragClass);

      if (e && typeof canvas.releasePointerCapture === "function") {
        try {
          canvas.releasePointerCapture(e.pointerId);
        } catch (err) {
          /* pointer may already be released */
        }
      }
    }

    function update() {
      if (dragging) return;
      if (Math.abs(velY) < MIN_VEL && Math.abs(velX) < MIN_VEL) return;

      rotY += velY;
      rotX += velX;
      velY *= FRICTION;
      velX *= FRICTION;
      applyRotation();
    }

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);
    canvas.addEventListener("lostpointercapture", endDrag);

    applyRotation();

    return { update: update };
  }

  function normalizeModel(model, targetHeight) {
    var box = new THREE.Box3().setFromObject(model);
    var size = box.getSize(new THREE.Vector3());
    var center = box.getCenter(new THREE.Vector3());
    var maxDim = Math.max(size.x, size.y, size.z);
    var scale = targetHeight / maxDim;

    model.scale.setScalar(scale);
    model.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);

    box.setFromObject(model);
    model.userData.groundY = box.min.y;
  }

  function loadHeroModel() {
    return new Promise(function (resolve, reject) {
      var loader = new GLTFLoader();
      loader.load(
        MODEL_URL,
        function (gltf) {
          var model = gltf.scene;
          prepareModel(model);
          normalizeModel(model, 3.2);
          resolve({
            model: model,
            animations: gltf.animations || [],
          });
        },
        undefined,
        reject
      );
    });
  }

  function createJointBlock() {
    var group = new THREE.Group();
    var clay = clayMaterial(0.4);

    var base = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.22, 0.7), clay);
    base.position.y = 0.11;
    group.add(base);

    var stem = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.55, 0.28), clay);
    stem.position.y = 0.45;
    group.add(stem);

    var cap = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.14, 0.38), clay);
    cap.position.y = 0.76;
    group.add(cap);

    var arm = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.12, 0.12), clay);
    arm.position.set(0.28, 0.52, 0);
    group.add(arm);

    return group;
  }

  function setupScene(canvas, options) {
    var w = canvas.clientWidth || 300;
    var h = canvas.clientHeight || 300;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);

    var renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(
      options.fov || 32,
      w / h,
      0.1,
      100
    );
    camera.position.set(
      options.camX || 3.2,
      options.camY || 2.4,
      options.camZ || 4.5
    );
    camera.lookAt(0, 1.2, 0);

    var hemi = new THREE.HemisphereLight(0xffffff, 0xd8d8d4, 0.85);
    scene.add(hemi);

    var key = new THREE.DirectionalLight(0xffffff, 0.85);
    key.position.set(4, 8, 6);
    scene.add(key);

    var fill = new THREE.DirectionalLight(0xffffff, 0.4);
    fill.position.set(-5, 3, -2);
    scene.add(fill);

    if (options.ground) {
      var ground = new THREE.Mesh(
        new THREE.PlaneGeometry(6, 6),
        new THREE.ShadowMaterial({ opacity: 0.08 })
      );
      ground.rotation.x = -Math.PI / 2;
      ground.position.y = 0;
      ground.receiveShadow = true;
      scene.add(ground);
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      key.castShadow = true;
      key.shadow.mapSize.width = 512;
      key.shadow.mapSize.height = 512;
    }

    return { renderer: renderer, scene: scene, camera: camera, w: w, h: h };
  }

  function initBuilding(model, animations) {
    stageCanvas = document.getElementById("hero-building-canvas");
    if (!stageCanvas) return null;

    var state = setupScene(stageCanvas, {
      fov: 28,
      camX: 4.2,
      camY: 2.6,
      camZ: 5.8,
      ground: true,
    });

    state.scene.add(model);
    state.group = model;
    state.baseRotY = 0.48;
    state.mixer = startModelAnimations(model, animations);
    state.clock = new THREE.Clock();
    state.spinner = createModelSpinner(stageCanvas, model, {
      baseRotY: state.baseRotY,
    });

    return state;
  }

  function initDetail() {
    detailCanvas = document.getElementById("hero-detail-canvas");
    if (!detailCanvas) return null;

    var state = setupScene(detailCanvas, {
      fov: 28,
      camX: 1.4,
      camY: 1.1,
      camZ: 1.8,
    });

    var joint = createJointBlock();
    state.scene.add(joint);
    state.group = joint;
    state.rotationSpeed = 0;

    return state;
  }

  function showSvgFallback() {
    var stage = document.querySelector(".hero__stage");
    if (stage) stage.classList.add("hero__stage--fallback");
    var detail = document.querySelector(".hero__detail-thumb");
    if (detail) detail.classList.add("hero__detail-thumb--fallback");
  }

  function resizeCanvas(state, canvas) {
    if (!state || !canvas) return;
    var w = canvas.clientWidth;
    var h = canvas.clientHeight;
    if (w === 0 || h === 0) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    state.renderer.setPixelRatio(dpr);
    state.renderer.setSize(w, h, false);
    state.camera.aspect = w / h;
    state.camera.updateProjectionMatrix();
    state.w = w;
    state.h = h;
  }

  function tick(now) {
    if (!heroVisible) {
      rafId = requestAnimationFrame(tick);
      return;
    }

    if (buildingState) {
      var bs = buildingState;
      if (bs.mixer && bs.clock) {
        bs.mixer.update(bs.clock.getDelta());
      }
      if (bs.spinner) {
        bs.spinner.update();
      }
      bs.renderer.render(bs.scene, bs.camera);
    }

    if (detailState) {
      detailState.group.rotation.y = 0.6;
      detailState.group.rotation.x = -0.25;
      detailState.renderer.render(detailState.scene, detailState.camera);
    }

    rafId = requestAnimationFrame(tick);
  }

  function onResize() {
    resizeCanvas(buildingState, stageCanvas);
    resizeCanvas(detailState, detailCanvas);
  }

  function observeVisibility() {
    if (!hero || typeof IntersectionObserver === "undefined") return;
    var obs = new IntersectionObserver(
      function (entries) {
        heroVisible = entries[0].isIntersecting;
      },
      { threshold: 0.05 }
    );
    obs.observe(hero);
  }

  function init() {
    hero = document.getElementById("hero");
    initMarquee();

    if (!webglSupported()) {
      showSvgFallback();
      return;
    }

    loadHeroModel()
      .then(function (payload) {
        buildingState = initBuilding(payload.model, payload.animations);
        detailState = initDetail();

        onResize();
        window.addEventListener("resize", onResize);
        observeVisibility();
        rafId = requestAnimationFrame(tick);
      })
      .catch(function () {
        showSvgFallback();
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
