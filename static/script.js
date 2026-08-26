let questions = [];
let answers = {};
let currentIndex = 0;
let employeeName = "";
let companyName = "";
let timerInterval = null;
let totalTimeSeconds = 20 * 60;
let hasStarted = false;
let hasSubmitted = false;
let isSubmitting = false;

function getEl(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showEl(id) {
  const el = getEl(id);
  if (el) el.classList.remove("hidden");
}

function hideEl(id) {
  const el = getEl(id);
  if (el) el.classList.add("hidden");
}

function setText(id, value) {
  const el = getEl(id);
  if (el) el.innerText = value;
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  let data = null;

  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

document.addEventListener("DOMContentLoaded", () => {
  ["employeeName", "companyName"].forEach((id) => {
    const input = getEl(id);
    if (!input) return;

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        startAssessment();
      }
    });
  });

  updateTimerDisplay();
});

async function startAssessment() {
  const employeeInput = getEl("employeeName");
  const companyInput = getEl("companyName");
  const startBtn = getEl("startAssessmentBtn");

  employeeName = String(employeeInput?.value || "").trim();
  companyName = String(companyInput?.value || "").trim();

  if (!employeeName) {
    alert("Please enter your full name.");
    employeeInput?.focus();
    return;
  }

  if (!companyName) {
    alert("Please enter your company name.");
    companyInput?.focus();
    return;
  }

  if (hasStarted) return;

  const oldText = startBtn ? startBtn.innerText : "Start Assessment";

  if (startBtn) {
    startBtn.disabled = true;
    startBtn.innerText = "Starting...";
  }

  try {
    const saveResult = await fetchJSON("/save_employee", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee_name: employeeName,
        company_name: companyName,
      }),
    });

    if (!saveResult.ok) {
      throw new Error(
        (saveResult.data && saveResult.data.message) ||
          "Unable to save employee details.",
      );
    }

    const questionResult = await fetchJSON("/assessment_questions");

    if (!questionResult.ok) {
      throw new Error(
        (questionResult.data && questionResult.data.message) ||
          "Unable to load assessment questions.",
      );
    }

    questions = Array.isArray(questionResult.data?.questions)
      ? questionResult.data.questions
      : [];

    if (!questions.length) {
      throw new Error("No assessment questions are available.");
    }

    const timerMinutes = Number(questionResult.data?.timer_minutes || 20);
    totalTimeSeconds = Math.max(1, timerMinutes) * 60;
    setText("timerDurationText", `${timerMinutes} minute duration`);

    hasStarted = true;
    currentIndex = 0;
    answers = {};

    setText("savedEmployeeNameText", employeeName);
    setText("savedCompanyNameText", companyName);
    hideEl("startCard");
    showEl("savedStudentBanner");
    showEl("examArea");
    showEl("submitBtn");

    renderQuestion();
    renderQuestionPalette();
    updateProgress();
    startTimer();

    const examArea = getEl("examArea");
    if (examArea) {
      window.scrollTo({ top: examArea.offsetTop - 20, behavior: "smooth" });
    }
  } catch (error) {
    console.error("Assessment start error:", error);
    alert(error.message || "Unable to start assessment.");
    hasStarted = false;
  } finally {
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.innerText = oldText;
    }
  }
}

function renderQuestion() {
  const current = questions[currentIndex];
  if (!current) return;

  setText("questionCount", `Question ${currentIndex + 1} of ${questions.length}`);
  setText("categoryPill", current.category || "Cybersecurity Awareness");
  setText("questionText", current.question || "");

  const savedAnswer = answers[String(current.slot_number)] || "";
  const optionsContainer = getEl("optionsContainer");

  if (!optionsContainer) return;

  optionsContainer.innerHTML = `
    ${createOption(current.slot_number, "A", current.option_a, savedAnswer)}
    ${createOption(current.slot_number, "B", current.option_b, savedAnswer)}
    ${createOption(current.slot_number, "C", current.option_c, savedAnswer)}
    ${createOption(current.slot_number, "D", current.option_d, savedAnswer)}
  `;

  const prevBtn = getEl("prevBtn");
  const nextBtn = getEl("nextBtn");

  if (prevBtn) prevBtn.disabled = currentIndex === 0;
  if (nextBtn) nextBtn.disabled = currentIndex === questions.length - 1;

  renderQuestionPalette();
  updateProgress();
}

function createOption(slotNumber, letter, text, savedAnswer) {
  const isChecked = savedAnswer === letter;

  return `
    <label class="option-item ${isChecked ? "option-item-selected" : ""}">
      <input
        type="radio"
        name="question_${slotNumber}"
        value="${letter}"
        ${isChecked ? "checked" : ""}
        onchange="saveAnswer(${slotNumber}, '${letter}')"
      >
      <span class="option-letter">${letter}</span>
      <span class="option-text">${escapeHtml(text)}</span>
    </label>
  `;
}

function saveAnswer(slotNumber, answer) {
  answers[String(slotNumber)] = answer;
  renderQuestion();
}

function renderQuestionPalette() {
  const palette = getEl("questionPalette");
  if (!palette) return;

  palette.innerHTML = "";

  questions.forEach((question, index) => {
    const isCurrent = index === currentIndex;
    const isAnswered = !!answers[String(question.slot_number)];

    palette.innerHTML += `
      <button
        type="button"
        class="palette-btn ${isCurrent ? "palette-btn-current" : ""} ${isAnswered ? "palette-btn-answered" : ""}"
        onclick="jumpToQuestion(${index})"
      >
        ${index + 1}
      </button>
    `;
  });
}

function updateProgress() {
  const answeredCount = Object.keys(answers).length;
  const total = questions.length || 15;
  const percentage = Math.round((answeredCount / total) * 100);

  setText("progressText", `${answeredCount} / ${total} answered`);

  const fill = getEl("progressFill");
  if (fill) fill.style.width = `${percentage}%`;
}

function jumpToQuestion(index) {
  if (index < 0 || index >= questions.length) return;
  currentIndex = index;
  renderQuestion();
}

function nextQuestion() {
  if (currentIndex < questions.length - 1) {
    currentIndex += 1;
    renderQuestion();
  }
}

function prevQuestion() {
  if (currentIndex > 0) {
    currentIndex -= 1;
    renderQuestion();
  }
}

function startTimer() {
  if (timerInterval) return;

  updateTimerDisplay();

  timerInterval = setInterval(() => {
    totalTimeSeconds -= 1;

    if (totalTimeSeconds < 0) {
      totalTimeSeconds = 0;
    }

    updateTimerDisplay();

    if (totalTimeSeconds <= 0) {
      clearInterval(timerInterval);
      timerInterval = null;

      if (!hasSubmitted) {
        performSubmission(true);
      }
    }
  }, 1000);
}

function updateTimerDisplay() {
  const timer = getEl("timer");
  const timerBox = getEl("timerBox");
  if (!timer) return;

  const minutes = Math.floor(totalTimeSeconds / 60);
  const seconds = totalTimeSeconds % 60;

  timer.innerText = `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;

  if (timerBox) {
    timerBox.classList.toggle("timer-danger", totalTimeSeconds <= 120);
  }
}

async function submitAssessment() {
  if (!hasStarted) {
    alert("Please start the assessment first.");
    return;
  }

  if (hasSubmitted || isSubmitting) return;

  const unanswered = questions.length - Object.keys(answers).length;
  const message = unanswered
    ? `You have ${unanswered} unanswered question(s). Submit anyway?`
    : "Submit assessment now?";

  if (!confirm(message)) return;

  await performSubmission(false);
}

async function performSubmission(isForced = false) {
  if (isSubmitting || hasSubmitted) return;

  isSubmitting = true;

  const submitBtn = getEl("submitBtn");
  const oldText = submitBtn ? submitBtn.innerText : "Submit Assessment";

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = isForced ? "Time Up..." : "Submitting...";
  }

  try {
    const result = await fetchJSON("/submit_assessment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee_name: employeeName,
        company_name: companyName,
        answers,
      }),
    });

    if (!result.ok) {
      throw new Error(
        (result.data && result.data.message) ||
          "Unable to submit assessment.",
      );
    }

    hasSubmitted = true;

    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }

    renderResultPage(result.data);
  } catch (error) {
    console.error("Submission error:", error);
    alert(error.message || "Unable to submit assessment.");

    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = oldText;
    }
  } finally {
    isSubmitting = false;
  }
}

function renderResultPage(data) {
  const studentPage = document.querySelector(".student-page");
  if (!studentPage) return;

  const weakAreas = Array.isArray(data.weak_areas) ? data.weak_areas : [];
  const breakdown = Array.isArray(data.breakdown) ? data.breakdown : [];
  const riskClass = String(data.risk_level || "").toLowerCase();

  const weakAreasHtml = weakAreas.length
    ? weakAreas
        .map((area) => `<li>${escapeHtml(area)}</li>`)
        .join("")
    : "<li>No weak areas identified.</li>";

  const breakdownHtml = breakdown
    .map((item) => {
      const selected = item.selected_answer || "Not answered";
      const selectedText = item.selected_text
        ? ` - ${escapeHtml(item.selected_text)}`
        : "";
      const missedHtml = item.is_correct
        ? ""
        : `<p class="missed-answer">Correct answer: ${escapeHtml(item.correct_answer)} - ${escapeHtml(item.correct_text)}</p>`;

      return `
        <div class="breakdown-item ${item.is_correct ? "breakdown-correct" : "breakdown-incorrect"}">
          <div class="breakdown-top">
            <strong>Question ${Number(item.slot_number || 0)}</strong>
            <span>${escapeHtml(item.category || "")}</span>
          </div>
          <p>${escapeHtml(item.question || "")}</p>
          <p class="answer-line">
            Your answer: ${escapeHtml(selected)}${selectedText}
          </p>
          ${missedHtml}
        </div>
      `;
    })
    .join("");

  studentPage.innerHTML = `
    <div class="result-card-wrapper">
      <section class="question-view-card result-card-center">
        <div class="result-top-badge">Assessment Completed</div>
        <h1>VIEK Technologies Assessment Result</h1>
        <p class="result-line">Employee: <strong>${escapeHtml(data.employee_name || "")}</strong></p>
        <p class="result-line">Company: <strong>${escapeHtml(data.company_name || "")}</strong></p>

        <div class="result-metrics">
          <div>
            <span>Score</span>
            <strong>${Number(data.score || 0)} / ${Number(data.total || 0)}</strong>
          </div>
          <div>
            <span>Percentage</span>
            <strong>${Number(data.percentage || 0)}%</strong>
          </div>
          <div class="risk-${escapeHtml(riskClass)}">
            <span>Risk Level</span>
            <strong>${escapeHtml(data.risk_level || "-")}</strong>
          </div>
        </div>

        <div class="weak-area-panel">
          <h2>Weak Areas</h2>
          <ul>${weakAreasHtml}</ul>
        </div>

        <div class="breakdown-panel">
          <h2>Question Breakdown</h2>
          ${breakdownHtml}
        </div>
      </section>
    </div>
  `;

  window.scrollTo({ top: 0, behavior: "smooth" });
}

window.startAssessment = startAssessment;
window.saveAnswer = saveAnswer;
window.jumpToQuestion = jumpToQuestion;
window.nextQuestion = nextQuestion;
window.prevQuestion = prevQuestion;
window.submitAssessment = submitAssessment;
