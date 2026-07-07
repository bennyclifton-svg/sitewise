/*
 * SITEFORM landing — header / mobile nav (Prompt 2).
 * Toggles full-screen overlay; wires SITEFORM DISPLAY on nav wordmarks.
 */
(function () {
  "use strict";

  var menu;
  var toggle;
  var closeBtn;
  var links;
  var lastFocus;

  function isOpen() {
    return menu && !menu.hidden;
  }

  function setOpen(open) {
    if (!menu) return;
    menu.hidden = !open;
    menu.setAttribute("aria-hidden", open ? "false" : "true");
    document.body.classList.toggle("nav-open", open);
    if (toggle) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }
    if (open) {
      lastFocus = document.activeElement;
      if (closeBtn) closeBtn.focus();
    } else if (lastFocus && typeof lastFocus.focus === "function") {
      lastFocus.focus();
    }
  }

  function onKeydown(e) {
    if (e.key === "Escape" && isOpen()) {
      e.preventDefault();
      setOpen(false);
    }
  }

  function init() {
    menu = document.getElementById("mobile-menu");
    toggle = document.querySelector(".site-nav__toggle");
    closeBtn = document.querySelector(".mobile-menu__close");
    links = menu ? menu.querySelectorAll("a[href^='#']") : [];

    if (window.SiteformDisplay) {
      window.SiteformDisplay.renderAll(document);
    }

    if (toggle && menu) {
      toggle.addEventListener("click", function () {
        setOpen(!isOpen());
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        setOpen(false);
      });
    }

    for (var i = 0; i < links.length; i++) {
      links[i].addEventListener("click", function () {
        setOpen(false);
      });
    }

    document.addEventListener("keydown", onKeydown);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
