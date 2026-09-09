/**
 * flashcards.js — Flashcard flip widget
 * Depends on: FLASHCARDS global array set in results.html
 */

(function () {
  "use strict";

  // Guard: only run on results page
  if (typeof FLASHCARDS === "undefined" || !FLASHCARDS.length) return;

  const flashcard  = document.getElementById("flashcard");
  const fcQuestion = document.getElementById("fcQuestion");
  const fcAnswer   = document.getElementById("fcAnswer");
  const fcPrev     = document.getElementById("fcPrev");
  const fcNext     = document.getElementById("fcNext");
  const fcFlip     = document.getElementById("fcFlip");
  const fcCurrent  = document.getElementById("fcCurrent");

  if (!flashcard) return;

  let currentIndex = 0;
  let isFlipped    = false;

  /* ── Load a card ────────────────────────────────────────────── */
  function loadCard(index) {
    const card = FLASHCARDS[index];
    if (!card) return;

    // Reset flip state
    isFlipped = false;
    flashcard.classList.remove("flipped");

    fcQuestion.textContent = card.question || "—";
    fcAnswer.textContent   = card.answer   || "—";
    fcCurrent.textContent  = index + 1;
  }

  /* ── Flip ───────────────────────────────────────────────────── */
  function flipCard() {
    isFlipped = !isFlipped;
    flashcard.classList.toggle("flipped", isFlipped);
  }

  /* ── Previous ───────────────────────────────────────────────── */
  function prevCard() {
    currentIndex = (currentIndex - 1 + FLASHCARDS.length) % FLASHCARDS.length;
    loadCard(currentIndex);
  }

  /* ── Next ───────────────────────────────────────────────────── */
  function nextCard() {
    currentIndex = (currentIndex + 1) % FLASHCARDS.length;
    loadCard(currentIndex);
  }

  /* ── Event listeners ────────────────────────────────────────── */
  flashcard.addEventListener("click", flipCard);

  flashcard.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      flipCard();
    }
    if (e.key === "ArrowLeft")  prevCard();
    if (e.key === "ArrowRight") nextCard();
  });

  if (fcFlip) fcFlip.addEventListener("click", flipCard);
  if (fcPrev) fcPrev.addEventListener("click", prevCard);
  if (fcNext) fcNext.addEventListener("click", nextCard);

  /* ── Swipe support ──────────────────────────────────────────── */
  let touchStartX = 0;
  flashcard.addEventListener("touchstart", (e) => { touchStartX = e.changedTouches[0].clientX; });
  flashcard.addEventListener("touchend",   (e) => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) {
      if (dx < 0) nextCard();
      else        prevCard();
    } else {
      flipCard();
    }
  });

  /* ── Init ───────────────────────────────────────────────────── */
  loadCard(0);

})();
