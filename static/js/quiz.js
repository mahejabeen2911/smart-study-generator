/**
 * quiz.js — Interactive MCQ Quiz
 * Depends on: QUIZ_DATA global array set in results.html
 */

(function () {
  "use strict";

  if (typeof QUIZ_DATA === "undefined" || !QUIZ_DATA.length) return;

  const submitBtn    = document.getElementById("submitQuiz");
  const retryBtn     = document.getElementById("retryQuiz");
  const quizForm     = document.getElementById("quizForm");
  const quizResults  = document.getElementById("quizResults");
  const quizContainer = document.getElementById("quizContainer");

  if (!submitBtn || !quizForm) return;

  /* ── Submit quiz ────────────────────────────────────────────── */
  submitBtn.addEventListener("click", () => {
    const questions = document.querySelectorAll(".quiz-question");
    let unanswered = 0;
    const answers  = [];

    questions.forEach((qEl, i) => {
      const selected = qEl.querySelector(`input[name="q${i}"]:checked`);
      if (!selected) {
        unanswered++;
        qEl.style.border = "2px solid #dc2626";
        return;
      }
      qEl.style.border = "";

      const correctAnswer = qEl.dataset.correct;
      const isCorrect     = selected.value === correctAnswer;
      const topic         = qEl.dataset.topic || `Question ${i + 1}`;

      answers.push({ question_index: i, selected: selected.value, is_correct: isCorrect, topic });

      // Mark options
      qEl.querySelectorAll(".option-label").forEach((label) => {
        const radio = label.querySelector("input[type='radio']");
        if (radio.value === correctAnswer) {
          label.classList.add("correct");
        } else if (radio.checked && !isCorrect) {
          label.classList.add("wrong");
        }
        radio.disabled = true;
      });

      // Show feedback
      const feedback = qEl.querySelector(".quiz-feedback");
      if (feedback) {
        const feedbackText = feedback.querySelector(".feedback-text");
        if (feedbackText) {
          feedbackText.textContent = isCorrect ? "✓ Correct!" : `✗ Incorrect — Correct answer: ${correctAnswer}`;
          feedbackText.style.color = isCorrect ? "var(--success)" : "var(--danger)";
        }
        feedback.classList.remove("hidden");
      }
    });

    if (unanswered > 0) {
      alert(`Please answer all ${unanswered} unanswered question(s) before submitting.`);
      return;
    }

    submitBtn.disabled = true;

    // Calculate results
    const total   = answers.length;
    const correct = answers.filter((a) => a.is_correct).length;
    const wrong   = total - correct;
    const pct     = total ? Math.round((correct / total) * 100) : 0;

    // Identify weak / strong topics
    const topicPerformance = {};
    answers.forEach((a) => {
      if (!topicPerformance[a.topic]) topicPerformance[a.topic] = { correct: 0, total: 0 };
      topicPerformance[a.topic].total++;
      if (a.is_correct) topicPerformance[a.topic].correct++;
    });

    const weakTopics   = [];
    const strongTopics = [];
    Object.entries(topicPerformance).forEach(([topic, stats]) => {
      const rate = (stats.correct / stats.total) * 100;
      if (rate < 60)  weakTopics.push({ topic, rate: Math.round(rate) });
      else            strongTopics.push({ topic, rate: Math.round(rate) });
    });

    // Post to server
    fetch("/quiz/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    }).catch(() => {
      // Non-critical — results are shown client-side regardless
    });

    displayResults(total, correct, wrong, pct, weakTopics, strongTopics);
  });

  /* ── Display results ─────────────────────────────────────────── */
  function displayResults(total, correct, wrong, pct, weakTopics, strongTopics) {
    // Score display
    document.getElementById("scoreBig").textContent   = `${pct}%`;
    document.getElementById("correctCount").textContent = correct;
    document.getElementById("wrongCount").textContent   = wrong;
    document.getElementById("totalCount").textContent   = total;

    // Score label / grade
    let label = "";
    if (pct >= 90)      label = "Excellent! Outstanding performance.";
    else if (pct >= 75) label = "Great job! Well prepared.";
    else if (pct >= 60) label = "Good effort. Review weak topics.";
    else if (pct >= 40) label = "Needs improvement. Focus on weak areas.";
    else                label = "Keep practicing. Review the material again.";
    document.getElementById("scoreLabel").textContent = `Your Score: ${correct}/${total} — ${label}`;

    // Weak topics
    const weakBox  = document.getElementById("weakTopicsBox");
    const weakList = document.getElementById("weakTopicsList");
    if (weakTopics.length && weakBox && weakList) {
      weakList.innerHTML = weakTopics
        .map((t) => `<li><strong>${t.topic}</strong> — ${t.rate}% correct</li>`)
        .join("");
      weakBox.classList.remove("hidden");
    }

    // Strong topics
    const strongBox  = document.getElementById("strongTopicsBox");
    const strongList = document.getElementById("strongTopicsList");
    if (strongTopics.length && strongBox && strongList) {
      strongList.innerHTML = strongTopics
        .map((t) => `<li><strong>${t.topic}</strong> — ${t.rate}% correct</li>`)
        .join("");
      strongBox.classList.remove("hidden");
    }

    // AI recommendation
    const recBox = document.getElementById("aiRecommendation");
    if (recBox) {
      let rec = "";
      if (pct < 60 && weakTopics.length) {
        const wt = weakTopics.map((t) => t.topic).join(", ");
        rec = `💡 <strong>Recommendation:</strong> Your performance in <em>${wt}</em> needs attention. 
               Review the summary and flashcards for these topics, then attempt the quiz again.`;
      } else if (pct >= 75) {
        rec = `🎉 <strong>Great performance!</strong> Continue revising high-priority topics and 
               try the next section of your material.`;
      } else {
        rec = `📚 <strong>Tip:</strong> Review the topics where you made mistakes, go through the 
               flashcards once more, and retake the quiz to improve your score.`;
      }
      if (rec) {
        recBox.innerHTML = rec;
        recBox.classList.remove("hidden");
      }
    }

    // Show results panel
    if (quizResults) quizResults.classList.remove("hidden");
    if (quizResults) quizResults.scrollIntoView({ behavior: "smooth" });
  }

  /* ── Retry quiz ─────────────────────────────────────────────── */
  if (retryBtn) {
    retryBtn.addEventListener("click", () => {
      // Reset all option labels and radio buttons
      document.querySelectorAll(".option-label").forEach((label) => {
        label.classList.remove("correct", "wrong");
        const radio = label.querySelector("input[type='radio']");
        if (radio) { radio.checked = false; radio.disabled = false; }
      });

      // Hide feedback
      document.querySelectorAll(".quiz-feedback").forEach((fb) => fb.classList.add("hidden"));
      document.querySelectorAll(".quiz-question").forEach((q)  => { q.style.border = ""; });

      // Hide results, show form
      if (quizResults) quizResults.classList.add("hidden");
      if (submitBtn)   submitBtn.disabled = false;

      // Reset result panels
      ["weakTopicsBox", "strongTopicsBox", "aiRecommendation"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.classList.add("hidden");
      });
    });
  }

})();
