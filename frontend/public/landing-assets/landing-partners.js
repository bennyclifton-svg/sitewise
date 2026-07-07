/*
 * SITEFORM landing — partners / integrations strip (Prompt 4).
 * Hero chevron controls page this table row; touch swipe supported.
 */
(function () {
  "use strict";

  var MOBILE_BP = 720;
  var SWIPE_THRESHOLD = 48;

  var viewport;
  var track;
  var prevBtn;
  var nextBtn;
  var cells;
  var page = 0;
  var visibleCount = 4;
  var pageCount = 1;
  var reducedMotion =
    window.SiteformDisplay && window.SiteformDisplay.prefersReducedMotion();

  function readVisibleCount() {
    return window.matchMedia("(max-width: " + MOBILE_BP + "px)").matches ? 2 : 4;
  }

  function layout() {
    if (!viewport || !track || !cells.length) return;

    visibleCount = readVisibleCount();
    viewport.style.setProperty("--partners-visible", String(visibleCount));

    var viewportWidth = viewport.clientWidth;
    var cellWidth = viewportWidth / visibleCount;
    pageCount = Math.max(1, Math.ceil(cells.length / visibleCount));

    if (page > pageCount - 1) {
      page = pageCount - 1;
    }

    track.style.width = cellWidth * cells.length + "px";

    for (var i = 0; i < cells.length; i++) {
      cells[i].style.width = cellWidth + "px";
    }

    applyTransform(false);
    updateControls();
  }

  function applyTransform(animate) {
    if (!track || !viewport) return;

    if (reducedMotion || animate === false) {
      track.style.transition = "none";
    } else {
      track.style.transition = "";
    }

    var offset = page * viewport.clientWidth;
    track.style.transform = "translate3d(" + -offset + "px, 0, 0)";

    if (reducedMotion || animate === false) {
      track.offsetHeight;
      track.style.transition = reducedMotion ? "none" : "";
    }
  }

  function updateControls() {
    if (!prevBtn || !nextBtn) return;

    prevBtn.disabled = page <= 0;
    nextBtn.disabled = page >= pageCount - 1;
    prevBtn.setAttribute("aria-disabled", prevBtn.disabled ? "true" : "false");
    nextBtn.setAttribute("aria-disabled", nextBtn.disabled ? "true" : "false");
  }

  function goToPage(nextPage) {
    var clamped = Math.max(0, Math.min(pageCount - 1, nextPage));
    if (clamped === page) return;
    page = clamped;
    applyTransform(true);
    updateControls();
  }

  function onPrevClick() {
    goToPage(page - 1);
  }

  function onNextClick() {
    goToPage(page + 1);
  }

  function bindSwipe() {
    if (!viewport) return;

    var startX = 0;
    var startY = 0;
    var tracking = false;

    viewport.addEventListener(
      "touchstart",
      function (e) {
        if (!e.touches || e.touches.length !== 1) return;
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        tracking = true;
      },
      { passive: true }
    );

    viewport.addEventListener(
      "touchmove",
      function (e) {
        if (!tracking || !e.touches || e.touches.length !== 1) return;
        var dx = e.touches[0].clientX - startX;
        var dy = e.touches[0].clientY - startY;
        if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
          e.preventDefault();
        }
      },
      { passive: false }
    );

    viewport.addEventListener(
      "touchend",
      function (e) {
        if (!tracking) return;
        tracking = false;
        var touch = e.changedTouches && e.changedTouches[0];
        if (!touch) return;

        var dx = touch.clientX - startX;
        var dy = touch.clientY - startY;
        if (Math.abs(dx) < SWIPE_THRESHOLD || Math.abs(dx) < Math.abs(dy)) {
          return;
        }

        if (dx < 0) {
          onNextClick();
        } else {
          onPrevClick();
        }
      },
      { passive: true }
    );
  }

  function init() {
    viewport = document.querySelector(".partners__viewport");
    track = document.getElementById("partners-track");
    prevBtn = document.querySelector(".hero__partners-prev");
    nextBtn = document.querySelector(".hero__partners-next");

    if (!viewport || !track || !prevBtn || !nextBtn) return;

    cells = track.querySelectorAll(".partners__cell");
    if (!cells.length) return;

    prevBtn.addEventListener("click", onPrevClick);
    nextBtn.addEventListener("click", onNextClick);
    bindSwipe();

    layout();
    window.addEventListener("resize", layout);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
