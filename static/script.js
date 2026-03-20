let availableSubjects = [];
let selectedSubjectId = null;
let selectedSubjectName = "";
let questions = [];
let currentQuestionIndex = 0;
let userAnswers = {};
let time = 60 * 60;
let timerInterval = null;
let studentName = "";
let studentSaved = false;

async function loadAvailableSubjects() {
  const res = await fetch("/available_subjects");
  availableSubjects = await res.json();

  const select = document.getElementById("subjectSelect");
  select.innerHTML = "";

  if (availableSubjects.length === 0) {
    select.innerHTML = `<option value="">No available subjects yet</option>`;
    return;
  }

  availableSubjects.forEach((subject) => {
    select.innerHTML += `
            <option value="${subject.id}">
                ${subject.name} (${subject.total_questions} questions)
            </option>
        `;
  });
}

async function saveStudentName() {
  const nameInput = document.getElementById("studentName").value.trim();

  if (!nameInput) {
    alert("Please enter your name.");
    return;
  }

  const res = await fetch("/save_student", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      student_name: nameInput,
    }),
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.message || "Unable to save student name.");
    return;
  }

  studentName = nameInput;
  studentSaved = true;

  document.getElementById("savedStudentNameText").innerText = studentName;
  document.getElementById("savedStudentBanner").classList.remove("hidden");

  alert(data.message);
}

async function startSelectedSubject() {
  if (!studentSaved || !studentName) {
    alert("Please save your name first.");
    return;
  }

  const select = document.getElementById("subjectSelect");

  if (!select.value) {
    alert("No available subject found.");
    return;
  }

  selectedSubjectId = parseInt(select.value);
  const subject = availableSubjects.find((s) => s.id === selectedSubjectId);
  selectedSubjectName = subject ? subject.name : "Subject";

  const res = await fetch(`/get_questions_by_subject/${selectedSubjectId}`);
  questions = await res.json();

  if (!questions.length) {
    alert("This subject has no questions yet.");
    return;
  }

  currentQuestionIndex = 0;
  userAnswers = {};

  document.getElementById("examArea").classList.remove("hidden");
  document.getElementById("submitBtn").classList.remove("hidden");

  resetTimer();
  renderQuestion();
}

function renderQuestion() {
  if (!questions.length) return;

  const current = questions[currentQuestionIndex];

  document.getElementById("questionCount").innerText =
    `Question ${currentQuestionIndex + 1} of ${questions.length}`;

  document.getElementById("subjectNamePill").innerText = selectedSubjectName;
  document.getElementById("questionText").innerText = current.question;

  const savedAnswer = userAnswers[current.slot_number] || "";
  const optionsContainer = document.getElementById("optionsContainer");

  optionsContainer.innerHTML = `
        ${createOption(current.slot_number, "A", current.option_a, savedAnswer)}
        ${createOption(current.slot_number, "B", current.option_b, savedAnswer)}
        ${createOption(current.slot_number, "C", current.option_c, savedAnswer)}
        ${createOption(current.slot_number, "D", current.option_d, savedAnswer)}
    `;
}

function createOption(slotNumber, letter, text, savedAnswer) {
  return `
        <label class="option-item">
            <input
                type="radio"
                name="question_${slotNumber}"
                value="${letter}"
                ${savedAnswer === letter ? "checked" : ""}
                onchange="saveAnswer(${slotNumber}, '${letter}')"
            >
            <span class="option-letter">${letter}</span>
            <span>${text}</span>
        </label>
    `;
}

function saveAnswer(slotNumber, answer) {
  userAnswers[String(slotNumber)] = answer;
}

function nextQuestion() {
  if (!questions.length) return;

  if (currentQuestionIndex < questions.length - 1) {
    currentQuestionIndex++;
    renderQuestion();
  }
}

function prevQuestion() {
  if (!questions.length) return;

  if (currentQuestionIndex > 0) {
    currentQuestionIndex--;
    renderQuestion();
  }
}

function resetTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
  }

  time = 60 * 60;
  updateTimerDisplay();

  timerInterval = setInterval(() => {
    time--;
    updateTimerDisplay();

    if (time <= 0) {
      clearInterval(timerInterval);
      submitExam();
    }
  }, 1000);
}

function updateTimerDisplay() {
  const minutes = Math.floor(time / 60);
  const seconds = time % 60;
  document.getElementById("timer").innerText =
    `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;
}

async function submitExam() {
  if (!selectedSubjectId) {
    alert("Please start a subject first.");
    return;
  }

  if (!studentName) {
    alert("Please save your name first.");
    return;
  }

  const res = await fetch("/submit_exam", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject_id: selectedSubjectId,
      student_name: studentName,
      answers: userAnswers,
    }),
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.message || "Unable to submit exam.");
    return;
  }

  if (timerInterval) {
    clearInterval(timerInterval);
  }

  document.querySelector(".student-page").innerHTML = `
        <div class="question-view-card result-card-center">
            <h1>Exam Completed</h1>
            <p class="result-line">Student: <strong>${studentName}</strong></p>
            <p class="result-line">Subject: <strong>${selectedSubjectName}</strong></p>
            <h2 class="result-score">Your Score: ${data.score} / ${data.total}</h2>
            <button class="primary-btn" style="margin-top:20px;" onclick="window.location.reload()">
                Take Another Subject
            </button>
        </div>
    `;
}

loadAvailableSubjects();
