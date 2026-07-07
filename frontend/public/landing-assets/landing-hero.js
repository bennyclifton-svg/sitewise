/*
 * SITEFORM landing — hero band (Prompt 3).
 * Marquee, Three.js clay building, detail thumbnail, edge furniture.
 */
(function () {
  "use strict";

  var CLAY = 0xf2f2ef;
  var ORANGE = 0xf96416;
  var BLACK = 0x0c0c0c;

  var hero;
  var stageCanvas;
  var detailCanvas;
  var buildingState = null;
  var detailState = null;
  var rafId = 0;
  var heroVisible = true;
  var pointer = { x: 0, y: 0 };
  var reducedMotion =
    window.SiteformDisplay && window.SiteformDisplay.prefersReducedMotion();

  function loadThree(callback) {
    if (window.THREE) {
      callback(window.THREE);
      return;
    }
    var s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js";
    s.async = true;
    s.onload = function () {
      callback(window.THREE);
    };
    s.onerror = function () {
      callback(null);
    };
    document.head.appendChild(s);
  }

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

  function clayMaterial(THREE, roughness) {
    return new THREE.MeshStandardMaterial({
      color: CLAY,
      roughness: typeof roughness === "number" ? roughness : 0.9,
      metalness: 0,
    });
  }

  function windowRecessMaterial(THREE) {
    return new THREE.MeshStandardMaterial({
      color: BLACK,
      roughness: 0.95,
      metalness: 0,
    });
  }

  function addOrangePortal(THREE, group, dims, animParts) {
    var portalH = dims.height * 0.2;
    var portalW = dims.width * 0.11;
    var portalY = dims.height * 0.1;
    var faceZ = dims.depth / 2 + 0.05;

    var portalFrame = new THREE.Mesh(
      new THREE.BoxGeometry(portalW, portalH, 0.12),
      new THREE.MeshStandardMaterial({
        color: ORANGE,
        emissive: ORANGE,
        emissiveIntensity: 0.35,
        roughness: 0.75,
        metalness: 0,
      })
    );
    portalFrame.position.set(0, portalY, faceZ);
    portalFrame.userData.floorIndex = 0;
    group.add(portalFrame);
    animParts.push(portalFrame);

    var portalFace = new THREE.Mesh(
      new THREE.BoxGeometry(portalW * 0.62, portalH * 0.72, 0.06),
      new THREE.MeshStandardMaterial({
        color: BLACK,
        roughness: 0.95,
        metalness: 0,
      })
    );
    portalFace.position.set(0, portalY, faceZ + 0.06);
    portalFace.userData.floorIndex = 0;
    group.add(portalFace);
    animParts.push(portalFace);

    var glow = new THREE.Mesh(
      new THREE.PlaneGeometry(portalW * 1.6, portalH * 1.15),
      new THREE.MeshBasicMaterial({
        color: ORANGE,
        transparent: true,
        opacity: 0.12,
        depthWrite: false,
      })
    );
    glow.position.set(0, portalY, faceZ - 0.02);
    glow.userData.floorIndex = 0;
    group.add(glow);
    animParts.push(glow);

    if (!reducedMotion) {
      portalFrame.position.y = -2;
      portalFace.position.y = -2;
      glow.position.y = -2;
    }
    portalFrame.userData.targetY = portalY;
    portalFace.userData.targetY = portalY;
    glow.userData.targetY = portalY;
  }

  function loadHeroGenome(callback) {
    fetch("landing-assets/genomes/art_deco.json")
      .then(function (res) {
        if (!res.ok) throw new Error("genome fetch failed");
        return res.json();
      })
      .then(callback)
      .catch(function () {
        callback({
          period: "art_deco",
          massing: {
            footprint: "stepped",
            aspect: [1.2, 2.35, 1],
            roof: "ziggurat",
            symmetry: "bilateral",
          },
          rhythm: {
            bays: 7,
            windowShape: "slot",
            windowToWallRatio: 0.34,
            verticality: 0.86,
          },
          ornament: {
            motifs: ["fluting", "sunburst_crown", "setbacks"],
            density: 0.32,
          },
          material: { base: "#c7bfae", roughness: 0.68, windowEmissive: "#ffbf69" },
        });
      });
  }

  function createBuilding(THREE, genome) {
    if (!window.LandingGenomeBuilder) {
      return { group: new THREE.Group(), animParts: [] };
    }

    var clay = clayMaterial(THREE, genome.material.roughness);
    var built = window.LandingGenomeBuilder.buildFromGenome(
      THREE,
      genome,
      { clay: clay, window: windowRecessMaterial(THREE) },
      { reducedMotion: reducedMotion, targetHeight: 3.6, baseY: -0.35 }
    );

    addOrangePortal(THREE, built.group, built.dimensions, built.animParts);

    return { group: built.group, floors: built.animParts };
  }

  function createJointBlock(THREE) {
    var group = new THREE.Group();
    var clay = clayMaterial(THREE);

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

  function setupScene(THREE, canvas, options) {
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

    var key = new THREE.DirectionalLight(0xffffff, 0.55);
    key.position.set(4, 8, 6);
    scene.add(key);

    var fill = new THREE.DirectionalLight(0xffffff, 0.25);
    fill.position.set(-5, 3, -2);
    scene.add(fill);

    /* Contact shadow — soft ground read */
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

    return { THREE: THREE, renderer: renderer, scene: scene, camera: camera, w: w, h: h };
  }

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function initBuilding(THREE, genome) {
    stageCanvas = document.getElementById("hero-building-canvas");
    if (!stageCanvas) return null;

    var state = setupScene(THREE, stageCanvas, {
      fov: 30,
      camX: 3.6,
      camY: 2.4,
      camZ: 5.2,
      ground: true,
    });

    var built = createBuilding(THREE, genome);
    state.scene.add(built.group);
    state.group = built.group;
    state.floors = built.floors;
    state.assemblyStart = reducedMotion ? null : performance.now();
    state.assemblyDuration = 2000;
    state.rotationSpeed = (Math.PI * 2) / 45000;
    state.baseRotY = reducedMotion ? 0.55 : 0;

    return state;
  }

  function initDetail(THREE) {
    detailCanvas = document.getElementById("hero-detail-canvas");
    if (!detailCanvas) return null;

    var state = setupScene(THREE, detailCanvas, {
      fov: 28,
      camX: 1.4,
      camY: 1.1,
      camZ: 1.8,
    });

    var joint = createJointBlock(THREE);
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
      bs.group.rotation.y =
        bs.baseRotY +
        (reducedMotion ? 0 : now * bs.rotationSpeed) +
        pointer.x * 0.12;
      bs.group.rotation.x = pointer.y * 0.04;

      if (bs.assemblyStart !== null) {
        var elapsed = now - bs.assemblyStart;
        var progress = Math.min(elapsed / bs.assemblyDuration, 1);
        for (var i = 0; i < bs.floors.length; i++) {
          var mesh = bs.floors[i];
          var floorDelay = (mesh.userData.floorIndex || 0) * 0.08;
          var localT = Math.max(
            0,
            Math.min(1, (progress - floorDelay) / (1 - floorDelay * 0.5))
          );
          var eased = easeOutCubic(localT);
          var startY = mesh.userData.startY != null ? mesh.userData.startY : -2;
          mesh.position.y =
            startY + (mesh.userData.targetY - startY) * eased;
        }
        if (progress >= 1) bs.assemblyStart = null;
      }

      bs.renderer.render(bs.scene, bs.camera);
    }

    if (detailState) {
      detailState.group.rotation.y = 0.6 + pointer.x * 0.08;
      detailState.group.rotation.x = -0.25 + pointer.y * 0.05;
      detailState.renderer.render(detailState.scene, detailState.camera);
    }

    rafId = requestAnimationFrame(tick);
  }

  function onResize() {
    resizeCanvas(buildingState, stageCanvas);
    resizeCanvas(detailState, detailCanvas);
  }

  function onPointerMove(e) {
    var rect = hero ? hero.getBoundingClientRect() : null;
    if (!rect) return;
    pointer.x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
    pointer.y = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
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

    loadThree(function (THREE) {
      if (!THREE) {
        showSvgFallback();
        return;
      }

      loadHeroGenome(function (genome) {
        buildingState = initBuilding(THREE, genome);
        detailState = initDetail(THREE);

        if (buildingState && buildingState.floors) {
          for (var i = 0; i < buildingState.floors.length; i++) {
            buildingState.floors[i].userData.startY =
              buildingState.floors[i].position.y;
          }
        }

        onResize();
        window.addEventListener("resize", onResize);
        if (!reducedMotion) {
          hero.addEventListener("pointermove", onPointerMove);
        }
        observeVisibility();
        rafId = requestAnimationFrame(tick);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
