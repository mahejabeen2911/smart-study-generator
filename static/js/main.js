/**
 * main.js — StudyGenAI shared JavaScript
 * Handles: navigation, generator form validation, loading animation,
 *          drop zone, tab switching, results tab switching.
 */

(function () {
  "use strict";

  /* ── Light/dark theme toggle ──────────────────────────────── */
  const themeToggle = document.getElementById("themeToggle");
  const savedTheme = localStorage.getItem("studygen-theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

  function applyTheme(theme) {
    const isDark = theme === "dark";
    document.documentElement.dataset.theme = isDark ? "dark" : "light";
    if (themeToggle) {
      themeToggle.innerHTML = `<i class="fas fa-${isDark ? "sun" : "moon"}" aria-hidden="true"></i>`;
      themeToggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  applyTheme(savedTheme || (prefersDark ? "dark" : "light"));
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      localStorage.setItem("studygen-theme", nextTheme);
      applyTheme(nextTheme);
    });
  }

  /* ── Mobile nav toggle ───────────────────────────────────────── */
  const navToggle = document.getElementById("navToggle");
  const navLinks  = document.getElementById("navLinks");

  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  /* ── Generator page logic ───────────────────────────────────── */
  const studyForm      = document.getElementById("studyForm");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const submitBtn      = document.getElementById("submitBtn");

  if (studyForm) {
    initGeneratorPage();
  }

  /* ── Results tab switching ──────────────────────────────────── */
  const rTabs = document.querySelectorAll(".rtab");
  if (rTabs.length) {
    rTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        rTabs.forEach((t) => { t.classList.remove("active"); t.setAttribute("aria-selected", "false"); });
        tab.classList.add("active");
        tab.setAttribute("aria-selected", "true");

        const target = tab.dataset.section;
        document.querySelectorAll(".result-section").forEach((sec) => {
          const isTarget = sec.id === `section-${target}`;
          sec.classList.toggle("active", isTarget);
          sec.classList.toggle("hidden", !isTarget);
        });
      });
    });
  }

  /* ═══════════════════════════════════════════════════════════════
     Generator Page Functions
  ═══════════════════════════════════════════════════════════════ */
  function initGeneratorPage() {
    /* Tab switching */
    const tabBtns   = document.querySelectorAll(".tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");

    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabBtns.forEach((b)   => { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
        tabPanels.forEach((p) => p.classList.add("hidden"));
        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        const target = document.getElementById(`tab${capitalize(btn.dataset.tab)}`);
        if (target) target.classList.remove("hidden");
      });
    });

    /* Drop zone */
    const dropZone   = document.getElementById("dropZone");
    const fileInput  = document.getElementById("studyFile");
    const fileInfo   = document.getElementById("fileInfo");
    const fileName   = document.getElementById("fileName");
    const fileType   = document.getElementById("fileType");
    const fileSize   = document.getElementById("fileSize");
    const removeFile = document.getElementById("removeFile");

    if (dropZone) {
      dropZone.addEventListener("dragover",  (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
      dropZone.addEventListener("dragleave", ()  => dropZone.classList.remove("drag-over"));
      dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file) handleFileSelected(file);
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", () => {
        if (fileInput.files[0]) handleFileSelected(fileInput.files[0]);
      });
    }

    if (removeFile) {
      removeFile.addEventListener("click", () => {
        fileInput.value = "";
        fileInfo.classList.add("hidden");
        dropZone.classList.remove("hidden");
        hideError(document.getElementById("materialError"));
      });
    }

    function handleFileSelected(file) {
      const allowed = ["pdf", "txt", "jpg", "jpeg", "png"];
      const ext = file.name.split(".").pop().toLowerCase();
      const materialErr = document.getElementById("materialError");

      if (!allowed.includes(ext)) {
        showError(materialErr, "Unsupported file type. Please upload PDF, TXT, JPG, JPEG, or PNG.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        showError(materialErr, "File is too large. Maximum size is 10 MB.");
        return;
      }
      hideError(materialErr);
      fileName.textContent = file.name;
      fileType.textContent = ext.toUpperCase();
      fileSize.textContent = formatBytes(file.size);
      // Hide drop zone, show file info
      dropZone.classList.add("hidden");
      fileInfo.classList.remove("hidden");
    }

    /* Char counter for pasted text */
    const pastedText = document.getElementById("pastedText");
    const charCount  = document.getElementById("charCount");
    if (pastedText && charCount) {
      pastedText.addEventListener("input", () => {
        charCount.textContent = pastedText.value.length;
      });
    }

    /* Exam date countdown */
    const examDate     = document.getElementById("examDate");
    const examCountdown = document.getElementById("examCountdown");
    if (examDate && examCountdown) {
      examDate.addEventListener("change", updateCountdown);

      // Set min date to today
      const today = new Date().toISOString().split("T")[0];
      examDate.setAttribute("min", today);
    }

    function updateCountdown() {
      if (!examDate || !examCountdown) return;
      const val = examDate.value;
      if (!val) { examCountdown.textContent = ""; return; }
      const diff = Math.ceil((new Date(val) - new Date()) / 86400000);
      if (diff < 0) {
        examCountdown.textContent = "⚠ Exam date is in the past.";
      } else if (diff === 0) {
        examCountdown.textContent = "🎯 Exam is today!";
      } else {
        examCountdown.textContent = `📅 ${diff} day(s) until your exam.`;
      }
    }

    /* Form validation & submit */
    studyForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const materialErr = document.getElementById("materialError");
      const profileErr  = document.getElementById("profileError");
      hideError(materialErr);
      hideError(profileErr);

      let valid = true;

      /* Check material */
      const activeTab = document.querySelector(".tab-btn.active");
      const isUploadTab = !activeTab || activeTab.dataset.tab === "upload";

      if (!isUploadTab) {
        // Paste tab
        const text = document.getElementById("pastedText")?.value.trim() || "";
        if (text.length < 50) {
          showError(materialErr, "Please enter at least 50 characters of study material.");
          valid = false;
        }
      } else {
        // Upload tab — check file selected AND fileInfo visible (double check)
        const fileSelected = fileInput && fileInput.files && fileInput.files.length > 0;
        const fileInfoVisible = fileInfo && !fileInfo.classList.contains("hidden");
        if (!fileSelected && !fileInfoVisible) {
          showError(materialErr, "Please select a file first. Click the upload area to browse your files.");
          valid = false;
        }
      }

      /* Check study hours */
      const hoursInput = document.getElementById("studyHours");
      if (hoursInput) {
        const h = parseFloat(hoursInput.value);
        if (isNaN(h) || h < 0.5 || h > 16) {
          showError(profileErr, "Study hours must be between 0.5 and 16.");
          valid = false;
        }
      }

      /* Check exam date if entered */
      if (examDate && examDate.value) {
        const d = new Date(examDate.value);
        if (isNaN(d.getTime())) {
          showError(profileErr, "Please enter a valid exam date.");
          valid = false;
        }
      }

      if (!valid) return;

      /* Show loading overlay */
      if (loadingOverlay) loadingOverlay.classList.remove("hidden");
      if (submitBtn) { submitBtn.disabled = true; }
      startLoadingSteps();

      studyForm.submit();
    });
  }

  /* ── Loading step animation ─────────────────────────────────── */
  function startLoadingSteps() {
    const steps = ["ls1", "ls2", "ls3", "ls4"];
    const messages = [
      "Reading your material…",
      "Analyzing content…",
      "Generating study resources…",
      "Finishing up…",
    ];
    const loadingStep = document.getElementById("loadingStep");
    let current = 0;

    const interval = setInterval(() => {
      if (current > 0) {
        const prev = document.getElementById(steps[current - 1]);
        if (prev) { prev.classList.remove("active"); prev.classList.add("done"); }
      }
      if (current < steps.length) {
        const el = document.getElementById(steps[current]);
        if (el) el.classList.add("active");
        if (loadingStep && messages[current]) loadingStep.textContent = messages[current];
        current++;
      } else {
        clearInterval(interval);
      }
    }, 3500);
  }

  /* ── Helpers ─────────────────────────────────────────────────── */
  function showError(el, msg) {
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function hideError(el) {
    if (!el) return;
    el.classList.add("hidden");
    el.textContent = "";
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

})();
