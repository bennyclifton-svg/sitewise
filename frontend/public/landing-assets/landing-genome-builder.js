/*
 * Style-genome geometry builder for the landing hero (vanilla JS).
 * Geometry follows StyleGenome JSON — materials are supplied by the caller.
 * Ported from frontend/src/lib/style-genome/generator.ts (art_deco.json driver).
 */
(function (root) {
  "use strict";

  var DEG = Math.PI / 180;
  var LANDING_SEED = 42;

  function mulberry32(seed) {
    return function () {
      var t = (seed += 0x6d2b79f5);
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hashSeed(input) {
    var hash = 2166136261;
    for (var i = 0; i < input.length; i += 1) {
      hash ^= input.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function clamp(v, min, max) {
    return Math.min(max, Math.max(min, v));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function createDimensions(genome, rng) {
    var aspect = genome.massing.aspect;
    var familyScale = 1 + (rng() - 0.5) * 0.08;
    var heightBias = genome.rhythm.verticality * 0.35;
    return {
      width: 3.2 * aspect[0] * familyScale,
      height: 3.1 * aspect[1] * (0.9 + heightBias) * familyScale,
      depth: 2.9 * aspect[2] * (0.96 + rng() * 0.08),
    };
  }

  function getFloorCount(genome, dimensions) {
    return clamp(
      Math.round(2 + dimensions.height / 1.7 + genome.rhythm.verticality * 2),
      2,
      10
    );
  }

  function boxGeometry(THREE, width, height, depth, x, y, z, rotation) {
    var geo = new THREE.BoxGeometry(width, height, depth);
    if (x || y || z || rotation) {
      var matrix = new THREE.Matrix4();
      matrix.compose(
        new THREE.Vector3(x || 0, y || 0, z || 0),
        new THREE.Quaternion().setFromEuler(rotation || new THREE.Euler()),
        new THREE.Vector3(1, 1, 1)
      );
      geo.applyMatrix4(matrix);
    }
    return geo;
  }

  function centeredExtrudedShape(THREE, points, depth) {
    var shape = new THREE.Shape();
    shape.moveTo(points[0][0], points[0][1]);
    for (var i = 1; i < points.length; i += 1) {
      shape.lineTo(points[i][0], points[i][1]);
    }
    shape.closePath();
    var geo = new THREE.ExtrudeGeometry(shape, { depth: depth, bevelEnabled: false });
    geo.translate(0, 0, -depth / 2);
    geo.computeVertexNormals();
    return geo;
  }

  function createWindowGeometry(THREE, shape) {
    if (shape === "lancet") {
      return centeredExtrudedShape(
        THREE,
        [
          [-0.35, -0.5],
          [0.35, -0.5],
          [0.35, 0.08],
          [0, 0.5],
          [-0.35, 0.08],
        ],
        0.08
      );
    }
    if (shape === "round_arch") {
      var pts = [];
      for (var i = 0; i <= 10; i += 1) {
        var angle = Math.PI - (Math.PI * i) / 10;
        pts.push([Math.cos(angle) * 0.35, Math.sin(angle) * 0.35 + 0.12]);
      }
      pts.push([0.35, -0.5], [-0.35, -0.5]);
      return centeredExtrudedShape(THREE, pts, 0.08);
    }
    return new THREE.BoxGeometry(1, 1, 1);
  }

  function createMassingParts(THREE, genome, dims) {
    var w = dims.width;
    var h = dims.height;
    var d = dims.depth;
    var parts = [];

    if (genome.massing.footprint === "cruciform") {
      parts.push({
        geometry: boxGeometry(THREE, w * 0.62, h * 0.88, d, 0, h * 0.44, 0),
        floorIndex: 0,
        name: "nave",
      });
      parts.push({
        geometry: boxGeometry(THREE, w, h * 0.7, d * 0.44, 0, h * 0.35, 0),
        floorIndex: 1,
        name: "transept",
      });
      parts.push({
        geometry: boxGeometry(THREE, w * 0.34, h, d * 0.34, 0, h * 0.5, 0),
        floorIndex: 2,
        name: "tower",
      });
    }

    if (genome.massing.footprint === "stepped") {
      var tiers = 4;
      var y = 0;
      for (var tier = 0; tier < tiers; tier += 1) {
        var t = tier / Math.max(1, tiers - 1);
        var tierHeight = h * (0.38 - t * 0.08);
        var tierWidth = w * (1 - t * 0.22);
        var tierDepth = d * (1 - t * 0.18);
        parts.push({
          geometry: boxGeometry(THREE, tierWidth, tierHeight, tierDepth, 0, y + tierHeight / 2, 0),
          floorIndex: tier,
          name: "tier-" + tier,
        });
        y += tierHeight * 0.78;
      }
    }

    return parts;
  }

  function getSteppedTopY(h, tiers) {
    var y = 0;
    for (var tier = 0; tier < tiers; tier += 1) {
      var t = tier / Math.max(1, tiers - 1);
      var tierHeight = h * (0.38 - t * 0.08);
      y += tierHeight * 0.78;
    }
    return y;
  }

  function getMassingTopY(genome, dims) {
    if (genome.massing.footprint === "stepped") {
      return getSteppedTopY(dims.height, 4);
    }
    return dims.height;
  }

  function createRoofParts(THREE, genome, dims) {
    var w = dims.width;
    var h = dims.height;
    var d = dims.depth;
    var parts = [];
    var massingTop = getMassingTopY(genome, dims);

    if (genome.massing.roof === "spire") {
      var offsets =
        genome.massing.footprint === "cruciform" ? [-0.34, 0, 0.34] : [0];
      for (var i = 0; i < offsets.length; i += 1) {
        var spire = new THREE.ConeGeometry(w * 0.12, h * 0.38, 4, 1);
        spire.translate(w * offsets[i], h + h * 0.19, 0);
        parts.push({
          geometry: spire,
          floorIndex: 3 + i,
          name: "spire-" + i,
        });
      }
    }

    if (genome.massing.roof === "ziggurat") {
      for (var zi = 0; zi < 4; zi += 1) {
        var zt = zi / 4;
        var crown = boxGeometry(
          THREE,
          w * (0.68 - zt * 0.11),
          h * 0.06,
          d * (0.68 - zt * 0.1),
          0,
          massingTop + h * (0.035 + zi * 0.055),
          0
        );
        parts.push({
          geometry: crown,
          floorIndex: 4 + zi,
          name: "crown-" + zi,
        });
      }
    }

    return parts;
  }

  function writeInstances(THREE, mesh, instances) {
    var matrix = new THREE.Matrix4();
    var quat = new THREE.Quaternion();
    for (var i = 0; i < instances.length; i += 1) {
      var inst = instances[i];
      quat.setFromEuler(inst.rotation || new THREE.Euler());
      matrix.compose(inst.position, quat, inst.scale);
      mesh.setMatrixAt(i, matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
  }

  function facadeInstance(x, y, z, width, height, rotY) {
    return {
      position: new THREE.Vector3(x, y, z),
      scale: new THREE.Vector3(width, height, 0.05),
      rotation: new THREE.Euler(0, rotY || 0, 0),
    };
  }

  function createWindowInstances(THREE, genome, dims, floors, rng, material) {
    var geometry = createWindowGeometry(THREE, genome.rhythm.windowShape);
    var instances = [];
    var w = dims.width;
    var h = dims.height;
    var d = dims.depth;
    var bays = clamp(Math.round(genome.rhythm.bays + (rng() - 0.5) * 1.2), 2, 11);
    var floorGap = h / (floors + 0.7);
    var bayGap = w / (bays + 1);
    var windowHeight = floorGap * lerp(0.34, 0.76, genome.rhythm.verticality);
    var windowWidth = bayGap * lerp(0.28, 0.7, genome.rhythm.windowToWallRatio);

    for (var floor = 0; floor < floors; floor += 1) {
      var y = floorGap * (floor + 0.82);
      for (var bay = 0; bay < bays; bay += 1) {
        var x = -w / 2 + bayGap * (bay + 1);
        var localWidth =
          genome.rhythm.windowShape === "slot" ? windowWidth * 0.38 : windowWidth;
        instances.push(facadeInstance(x, y, d / 2 + 0.036, localWidth, windowHeight, 0));
      }
    }

    if (instances.length === 0) return null;

    var mesh = new THREE.InstancedMesh(geometry, material, instances.length);
    mesh.name = "rhythm-windows";
    writeInstances(THREE, mesh, instances);
    mesh.userData.floorIndex = 4;
    return mesh;
  }

  function addLancetArchFrames(THREE, genome, dims, material) {
    var w = dims.width;
    var h = dims.height;
    var d = dims.depth;
    var count = clamp(genome.rhythm.bays, 3, 8);
    var geometry = createWindowGeometry(
      THREE,
      genome.rhythm.windowShape === "round_arch" ? "round_arch" : "lancet"
    );
    var instances = [];
    for (var i = 0; i < count; i += 1) {
      var x = -w * 0.38 + (w * 0.76 * i) / Math.max(1, count - 1);
      instances.push(
        facadeInstance(x, h * 0.22, d / 2 + 0.085, w * 0.09, h * 0.22, 0)
      );
    }
    var mesh = new THREE.InstancedMesh(geometry, material, instances.length);
    mesh.name = "motif-lancet-arch";
    writeInstances(THREE, mesh, instances);
    mesh.userData.floorIndex = 5;
    return mesh;
  }

  function addRoseWindow(THREE, dims, material) {
    var h = dims.height;
    var d = dims.depth;
    var geometry = new THREE.CylinderGeometry(0.32, 0.32, 0.06, 24);
    geometry.rotateX(Math.PI / 2);
    geometry.translate(0, h * 0.68, d / 2 + 0.09);
    var mesh = new THREE.Mesh(geometry, material);
    mesh.name = "motif-rose-window";
    mesh.userData.floorIndex = 6;
    return mesh;
  }

  function addFlyingButtresses(THREE, genome, dims, material) {
    var w = dims.width;
    var h = dims.height;
    var d = dims.depth;
    var count = clamp(genome.rhythm.bays, 4, 7);
    var geometry = new THREE.BoxGeometry(1, 1, 1);
    var instances = [];
    for (var i = 0; i < count; i += 1) {
      var z = -d * 0.42 + (d * 0.84 * i) / Math.max(1, count - 1);
      for (var s = 0; s < 2; s += 1) {
        var side = s === 0 ? -1 : 1;
        instances.push({
          position: new THREE.Vector3(side * w * 0.38, h * 0.36, z),
          scale: new THREE.Vector3(0.08, h * 0.64, 0.08),
          rotation: new THREE.Euler(0, 0, side * -18 * DEG),
        });
      }
    }
    var mesh = new THREE.InstancedMesh(geometry, material, instances.length);
    mesh.name = "motif-buttress";
    writeInstances(THREE, mesh, instances);
    mesh.userData.floorIndex = 7;
    return mesh;
  }

  function registerAnimPart(animParts, object, reducedMotion) {
    var targetY = object.position.y;
    object.userData.targetY = targetY;
    if (!reducedMotion) {
      object.position.y = -2 - (object.userData.floorIndex || 0) * 0.08;
    }
    animParts.push(object);
  }

  /**
   * Build hero geometry from a StyleGenome JSON object.
   * materials: { clay, window, dark } — landing page keeps clay/orange palette.
   */
  function buildFromGenome(THREE, genome, materials, options) {
    options = options || {};
    var reducedMotion = !!options.reducedMotion;
    var rng = mulberry32(hashSeed(genome.period + ":" + (options.seed || LANDING_SEED)));

    var dims = createDimensions(genome, rng);
    var targetHeight = options.targetHeight || 3.5;
    var scale = targetHeight / dims.height;

    var group = new THREE.Group();
    group.name = "style-genome:" + genome.period;
    group.scale.setScalar(scale);

    var animParts = [];
    var roughness =
      typeof genome.material.roughness === "number" ? genome.material.roughness : 0.9;

    if (materials.clay) {
      materials.clay.roughness = roughness;
    }

    var massing = createMassingParts(THREE, genome, dims);
    for (var m = 0; m < massing.length; m += 1) {
      var part = massing[m];
      var mesh = new THREE.Mesh(part.geometry, materials.clay);
      mesh.name = part.name;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.userData.floorIndex = part.floorIndex;
      group.add(mesh);
      registerAnimPart(animParts, mesh, reducedMotion);
    }

    var roofs = createRoofParts(THREE, genome, dims);
    for (var r = 0; r < roofs.length; r += 1) {
      var roofMesh = new THREE.Mesh(roofs[r].geometry, materials.clay);
      roofMesh.name = roofs[r].name;
      roofMesh.castShadow = true;
      roofMesh.userData.floorIndex = roofs[r].floorIndex;
      group.add(roofMesh);
      registerAnimPart(animParts, roofMesh, reducedMotion);
    }

    var floors = getFloorCount(genome, dims);
    var windows = createWindowInstances(
      THREE,
      genome,
      dims,
      floors,
      rng,
      materials.window
    );
    if (windows) {
      group.add(windows);
      registerAnimPart(animParts, windows, reducedMotion);
    }

    var motifs = (genome.ornament.motifs || []).slice(0, 3);
    for (var i = 0; i < motifs.length; i += 1) {
      var motif = motifs[i];
      var motifMesh = null;
      if (motif === "lancet_arch") {
        motifMesh = addLancetArchFrames(THREE, genome, dims, materials.clay);
      } else if (motif === "rose_window") {
        motifMesh = addRoseWindow(THREE, dims, materials.clay);
      } else if (motif === "flying_buttress") {
        motifMesh = addFlyingButtresses(THREE, genome, dims, materials.clay);
      }
      if (motifMesh) {
        motifMesh.castShadow = true;
        group.add(motifMesh);
        registerAnimPart(animParts, motifMesh, reducedMotion);
      }
    }

    group.position.y = options.baseY != null ? options.baseY : -0.15;
    return { group: group, animParts: animParts, dimensions: dims, scale: scale };
  }

  root.LandingGenomeBuilder = {
    buildFromGenome: buildFromGenome,
    LANDING_SEED: LANDING_SEED,
  };
})(typeof window !== "undefined" ? window : globalThis);
