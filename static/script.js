let availableSubjects = [];
let selectedSubjectId = null;
let selectedSubjectName = "";
let studentName = "";
let studentSaved = false;
let subjectQuestionsCache = {};
let subjectCurrentIndex = {};
let allAnswers = {};
let timerInterval = null;
let totalTimeSeconds = 60 * 60;
let hasSubmitted = false;
let isSavingStudent = false;
let isLoadingSubject = false;
let isSubmittingExam = false;

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
  const nameInput = getEl("studentName");

  if (nameInput) {
    nameInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveStudentName();
      }
    });
  }

  loadAvailableSubjects();
  renderSubjectProgress();
  updateTimerDisplay();
});

async function loadAvailableSubjects() {
  const row = getEl("subjectRow");

  if (row) {
    row.innerHTML = `
      <div class="empty-subject-state">
        Loading available subjects...
      </div>
    `;
  }

  try {
    const result = await fetchJSON("/available_subjects");

    if (!result.ok) {
      throw new Error(
        (result.data && result.data.message) || "Unable to load subjects.",
      );
    }

    availableSubjects = Array.isArray(result.data) ? result.data : [];
    renderSubjectButtons();
    renderSubjectProgress();
  } catch (error) {
    console.error("Error loading subjects:", error);

    if (row) {
      row.innerHTML = `
        <div class="empty-subject-state">
          Unable to load subjects right now.
        </div>
      `;
    }
  }
}

function renderSubjectButtons() {
  const row = getEl("subjectRow");
  if (!row) return;

  row.innerHTML = "";

  if (!availableSubjects.length) {
    row.innerHTML = `
      <div class="empty-subject-state">
        No subjects available yet. Admin needs to add questions first.
      </div>
    `;
    return;
  }

  availableSubjects.forEach((subject) => {
    const isSelected = selectedSubjectId === subject.id;
    const answerCount = getAnsweredCountForSubject(subject.id);

    row.innerHTML += `
      <button
        type="button"
        class="subject-cbt-btn ${isSelected ? "subject-cbt-btn-active" : ""}"
        onclick="selectSubject(${subject.id})"
      >
        <span class="subject-cbt-name">${escapeHtml(subject.name)}</span>
        <span class="subject-cbt-meta">${Number(subject.saved_questions || 0)} Questions Set</span>
        <span class="subject-cbt-progress">${answerCount} Answered</span>
      </button>
    `;
  });
}

function renderSubjectProgress() {
  const container = getEl("subjectProgressList");
  if (!container) return;

  container.innerHTML = "";

  if (!availableSubjects.length) {
    container.innerHTML = `
      <div class="mini-empty-state">No subject progress yet.</div>
    `;
    return;
  }

  availableSubjects.forEach((subject) => {
    const answered = getAnsweredCountForSubject(subject.id);

    container.innerHTML += `
      <div class="subject-progress-item ${selectedSubjectId === subject.id ? "subject-progress-item-active" : ""}">
        <div class="subject-progress-name">${escapeHtml(subject.name)}</div>
        <div class="subject-progress-meta">${answered} / ${Number(subject.saved_questions || 0)} answered</div>
      </div>
    `;
  });
}

function getAnsweredCountForSubject(subjectId) {
  const key = String(subjectId);
  if (!allAnswers[key]) return 0;
  return Object.keys(allAnswers[key]).length;
}

async function saveStudentName() {
  const nameField = getEl("studentName");
  const saveBtn = getEl("saveNameBtn");

  if (!nameField) {
    alert("Student name input is missing.");
    return;
  }

  const nameInput = String(nameField.value || "").trim();

  if (!nameInput) {
    alert("Please enter your full name.");
    nameField.focus();
    return;
  }

  if (isSavingStudent) return;
  isSavingStudent = true;

  const oldBtnText = saveBtn ? saveBtn.innerText : "Save Name";

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerText = "Saving...";
  }

  try {
    let result = await fetchJSON("/save_student", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        student_name: nameInput,
        allow_existing: false,
      }),
    });

    if (result.status === 409 && result.data && result.data.exists) {
      const existingName = result.data.existing_name || nameInput;

      const confirmed = confirm(
        `${existingName} already exists.\n\nIf this is the same student retaking the exam, press OK.\nIf not, press Cancel and use another name.`,
      );

      if (!confirmed) {
        return;
      }

      result = await fetchJSON("/save_student", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          student_name: existingName,
          allow_existing: true,
        }),
      });
    }

    if (!result.ok) {
      throw new Error(
        (result.data && result.data.message) || "Unable to save student name.",
      );
    }

    studentName = (result.data && result.data.student_name) || nameInput;
    studentSaved = true;

    setText("savedStudentNameText", studentName);
    showEl("savedStudentBanner");
    hideEl("nameSaveCard");
    showEl("submitBtn");

    if (!timerInterval) {
      startTimer();
    }

    alert(
      (result.data && result.data.message) ||
        "Student name saved successfully.",
    );
  } catch (error) {
    console.error("Error saving name:", error);
    alert(error.message || "Unable to save student name.");
  } finally {
    isSavingStudent = false;

    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerText = oldBtnText;
    }
  }
}

async function selectSubject(subjectId) {
  if (!studentSaved) {
    alert("Please save your name first.");
    return;
  }

  if (isLoadingSubject) return;
  isLoadingSubject = true;

  try {
    selectedSubjectId = subjectId;
    const subject = availableSubjects.find((s) => s.id === subjectId);
    selectedSubjectName = subject ? subject.name : `Subject ${subjectId}`;

    const subjectKey = String(subjectId);

    if (!subjectQuestionsCache[subjectKey]) {
      const result = await fetchJSON(`/get_questions_by_subject/${subjectId}`);

      if (!result.ok) {
        throw new Error(
          (result.data && result.data.message) ||
            "Unable to load questions for this subject.",
        );
      }

      const questions = Array.isArray(result.data) ? result.data : [];

      if (!questions.length) {
        alert("No questions found for this subject.");
        return;
      }

      subjectQuestionsCache[subjectKey] = questions;

      if (typeof subjectCurrentIndex[subjectKey] !== "number") {
        subjectCurrentIndex[subjectKey] = 0;
      }
    }

    showEl("examArea");
    renderSubjectButtons();
    renderSubjectProgress();
    renderQuestion();
    renderQuestionPalette();

    const examArea = getEl("examArea");
    if (examArea) {
      window.scrollTo({
        top: examArea.offsetTop - 20,
        behavior: "smooth",
      });
    }
  } catch (error) {
    console.error("Error selecting subject:", error);
    alert(error.message || "Unable to open subject.");
  } finally {
    isLoadingSubject = false;
  }
}

function renderQuestion() {
  if (!selectedSubjectId) return;

  const subjectKey = String(selectedSubjectId);
  const questions = subjectQuestionsCache[subjectKey] || [];
  const currentIndex = subjectCurrentIndex[subjectKey] || 0;
  const current = questions[currentIndex];

  if (!current) return;

  setText(
    "questionCount",
    `Question ${currentIndex + 1} of ${questions.length}`,
  );
  setText("subjectNamePill", selectedSubjectName || "Subject");
  setText("questionText", current.question || "Question text");

  if (!allAnswers[subjectKey]) {
    allAnswers[subjectKey] = {};
  }

  const savedAnswer = allAnswers[subjectKey][String(current.slot_number)] || "";
  const optionsContainer = getEl("optionsContainer");

  if (!optionsContainer) return;

  optionsContainer.innerHTML = `
    ${createOption(current.slot_number, "A", current.option_a, savedAnswer)}
    ${createOption(current.slot_number, "B", current.option_b, savedAnswer)}
    ${createOption(current.slot_number, "C", current.option_c, savedAnswer)}
    ${createOption(current.slot_number, "D", current.option_d, savedAnswer)}
  `;

  renderQuestionPalette();
  renderSubjectButtons();
  renderSubjectProgress();
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
  if (!selectedSubjectId) return;

  const subjectKey = String(selectedSubjectId);

  if (!allAnswers[subjectKey]) {
    allAnswers[subjectKey] = {};
  }

  allAnswers[subjectKey][String(slotNumber)] = answer;
  renderQuestion();
}

function renderQuestionPalette() {
  const palette = getEl("questionPalette");
  if (!palette || !selectedSubjectId) return;

  const subjectKey = String(selectedSubjectId);
  const questions = subjectQuestionsCache[subjectKey] || [];
  const currentIndex = subjectCurrentIndex[subjectKey] || 0;
  const subjectAnswers = allAnswers[subjectKey] || {};

  palette.innerHTML = "";

  questions.forEach((question, index) => {
    const isCurrent = index === currentIndex;
    const isAnswered = !!subjectAnswers[String(question.slot_number)];

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

function jumpToQuestion(index) {
  if (!selectedSubjectId) return;

  const subjectKey = String(selectedSubjectId);
  const questions = subjectQuestionsCache[subjectKey] || [];

  if (index < 0 || index >= questions.length) return;

  subjectCurrentIndex[subjectKey] = index;
  renderQuestion();
}

function nextQuestion() {
  if (!selectedSubjectId) return;

  const subjectKey = String(selectedSubjectId);
  const questions = subjectQuestionsCache[subjectKey] || [];
  const currentIndex = subjectCurrentIndex[subjectKey] || 0;

  if (currentIndex < questions.length - 1) {
    subjectCurrentIndex[subjectKey] = currentIndex + 1;
    renderQuestion();
  }
}

function prevQuestion() {
  if (!selectedSubjectId) return;

  const subjectKey = String(selectedSubjectId);
  const currentIndex = subjectCurrentIndex[subjectKey] || 0;

  if (currentIndex > 0) {
    subjectCurrentIndex[subjectKey] = currentIndex - 1;
    renderQuestion();
  }
}

function startTimer() {
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
        forceSubmitAllSubjects();
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
    if (totalTimeSeconds <= 300) {
      timerBox.classList.add("timer-danger");
    } else {
      timerBox.classList.remove("timer-danger");
    }
  }
}

async function submitAllSubjects() {
  if (!studentSaved || !studentName) {
    alert("Please save your name first.");
    return;
  }

  if (!availableSubjects.length) {
    alert("No available subjects found.");
    return;
  }

  if (hasSubmitted || isSubmittingExam) return;

  const confirmed = confirm("Submit all subjects now?");
  if (!confirmed) return;

  await performSubmission(false);
}

async function forceSubmitAllSubjects() {
  if (hasSubmitted || isSubmittingExam) return;
  await performSubmission(true);
}

async function performSubmission(isForced = false) {
  isSubmittingExam = true;

  const submitBtn = getEl("submitBtn");
  const oldBtnText = submitBtn ? submitBtn.innerText : "Submit All Subjects";

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = isForced ? "Time Up..." : "Submitting...";
  }

  try {
    const result = await fetchJSON("/submit_all_subjects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_name: studentName,
        all_answers: allAnswers,
      }),
    });

    if (!result.ok) {
      throw new Error(
        (result.data && result.data.message) || "Unable to submit exam.",
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
    hasSubmitted = false;
    alert(error.message || "Unable to submit exam.");
  } finally {
    isSubmittingExam = false;

    if (!hasSubmitted && submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = oldBtnText;
    }
  }
}

function renderResultPage(data) {
  const studentPage = document.querySelector(".student-page");
  if (!studentPage) return;

  const summary = Array.isArray(data.summary) ? data.summary : [];
  let summaryHtml = "";

  summary.forEach((item) => {
    summaryHtml += `
      <tr>
        <td>${escapeHtml(item.subject_name || "")}</td>
        <td>${Number(item.score || 0)} / ${Number(item.total || 0)}</td>
        <td>${escapeHtml(item.grade || "-")}</td>
        <td>${Number(item.attempt_number || 0)}</td>
      </tr>
    `;
  });

  studentPage.innerHTML = `
    <div class="result-card-wrapper">
      <div class="question-view-card result-card-center">
        <div class="result-top-badge">Exam Completed Successfully</div>
        <h1>CBT Result Summary</h1>
        <p class="result-line">Student: <strong>${escapeHtml(data.student_name || "")}</strong></p>
        <h2 class="result-score">Grand Total: ${Number(data.grand_score || 0)} / ${Number(data.grand_total || 0)}</h2>
        <h3 class="result-grade-line">Overall Grade: ${escapeHtml(data.grand_grade || "-")}</h3>

        <div class="table-wrap result-table-wrap">
          <table class="results-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Score</th>
                <th>Grade</th>
                <th>Attempt Number</th>
              </tr>
            </thead>
            <tbody>
              ${summaryHtml}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

window.saveStudentName = saveStudentName;
window.selectSubject = selectSubject;
window.saveAnswer = saveAnswer;
window.jumpToQuestion = jumpToQuestion;
window.nextQuestion = nextQuestion;
window.prevQuestion = prevQuestion;
window.submitAllSubjects = submitAllSubjects;
