from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import sqlite3
from functools import wraps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = "viek_cyber_awareness_change_this_later"

ASSESSMENT_ID = 1
ASSESSMENT_NAME = "VIEK Technologies AI Cybersecurity Awareness Assessment"

CYBER_QUESTIONS = [
    {
        "slot_number": 1,
        "category": "AI phishing",
        "question": "You receive an email that appears perfectly written, uses your company style, and asks you to open an attached invoice urgently. What should you do first?",
        "option_a": "Open the attachment because the email looks professional",
        "option_b": "Reply and ask the sender if it is genuine",
        "option_c": "Verify the request through a trusted channel before opening anything",
        "option_d": "Forward it to colleagues so they can check it too",
        "answer": "C",
    },
    {
        "slot_number": 2,
        "category": "Phishing emails",
        "question": "Which sign most strongly suggests an email may be phishing?",
        "option_a": "It includes the company logo",
        "option_b": "It creates urgency and asks you to click a link to avoid account suspension",
        "option_c": "It has a greeting with your first name",
        "option_d": "It was received during business hours",
        "answer": "B",
    },
    {
        "slot_number": 3,
        "category": "Social engineering",
        "question": "A caller says they are from IT support and asks for your password to fix a system issue. What is the safest response?",
        "option_a": "Share the password if they know your department",
        "option_b": "Ask them to call back later",
        "option_c": "Refuse to share the password and report the request",
        "option_d": "Send the password by SMS instead",
        "answer": "C",
    },
    {
        "slot_number": 4,
        "category": "AI voice scams",
        "question": "You receive a voice note that sounds like your manager asking you to buy gift cards immediately for a client. What should you do?",
        "option_a": "Buy the cards because the voice sounds authentic",
        "option_b": "Verify with your manager through a known phone number or in person",
        "option_c": "Ask the sender to send a longer voice note",
        "option_d": "Forward the request to finance for payment",
        "answer": "B",
    },
    {
        "slot_number": 5,
        "category": "Deepfakes",
        "question": "During a video call, a senior executive asks you to bypass payment controls for a confidential deal. What is the best action?",
        "option_a": "Proceed because video calls are reliable proof of identity",
        "option_b": "Record the call and share it publicly",
        "option_c": "Pause and verify the instruction using the approved approval process",
        "option_d": "Ask the executive to repeat the instruction more clearly",
        "answer": "C",
    },
    {
        "slot_number": 6,
        "category": "Safe use of AI tools",
        "question": "You want to use an AI chatbot to summarize a client contract. What should you do before pasting the document?",
        "option_a": "Paste it if the chatbot gives good answers",
        "option_b": "Remove or mask confidential data and follow company AI-use policy",
        "option_c": "Paste only the signature page",
        "option_d": "Ask the chatbot not to store the information",
        "answer": "B",
    },
    {
        "slot_number": 7,
        "category": "Sensitive information handling",
        "question": "A colleague asks you to send customer records to their personal email because their work email is full. What should you do?",
        "option_a": "Send it because they are your colleague",
        "option_b": "Send only a small sample",
        "option_c": "Refuse and use approved company channels for sensitive data",
        "option_d": "Zip the file without a password",
        "answer": "C",
    },
    {
        "slot_number": 8,
        "category": "Password security",
        "question": "Which password practice is safest for work accounts?",
        "option_a": "Use the same strong password everywhere",
        "option_b": "Use a unique password for each account and store it in an approved password manager",
        "option_c": "Write passwords in a notebook kept on your desk",
        "option_d": "Share passwords only with trusted team members",
        "answer": "B",
    },
    {
        "slot_number": 9,
        "category": "MFA",
        "question": "You receive an MFA approval prompt you did not initiate. What should you do?",
        "option_a": "Approve it so your account does not get locked",
        "option_b": "Deny it, change your password, and report the incident",
        "option_c": "Ignore it and continue working",
        "option_d": "Ask a coworker to approve it for you",
        "answer": "B",
    },
    {
        "slot_number": 10,
        "category": "Business Email Compromise",
        "question": "Your CEO sends you a WhatsApp message asking you to urgently transfer NGN 1,000,000 to a new bank account. What should you do?",
        "option_a": "Transfer the money immediately",
        "option_b": "Ask the CEO for the account number again",
        "option_c": "Verify the request through another trusted communication channel",
        "option_d": "Ignore the message without telling anyone",
        "answer": "C",
    },
    {
        "slot_number": 11,
        "category": "Suspicious links",
        "question": "A link in an email says it goes to your payroll portal, but hovering over it shows an unfamiliar domain. What should you do?",
        "option_a": "Click it and check whether the page looks correct",
        "option_b": "Open the official payroll site by typing the known address yourself",
        "option_c": "Forward it to your personal email to test later",
        "option_d": "Reply to the email asking if the link is safe",
        "answer": "B",
    },
    {
        "slot_number": 12,
        "category": "Reporting suspicious activity",
        "question": "You accidentally clicked a suspicious link but closed the page quickly. What should you do next?",
        "option_a": "Do nothing because the page was closed",
        "option_b": "Wait to see if anything bad happens",
        "option_c": "Report it immediately to IT or the security contact",
        "option_d": "Delete the email and clear browser history",
        "answer": "C",
    },
    {
        "slot_number": 13,
        "category": "AI data privacy",
        "question": "Which information should not be entered into a public AI tool without approval?",
        "option_a": "A public press release",
        "option_b": "Generic cybersecurity tips",
        "option_c": "Customer personal data, internal financials, or confidential plans",
        "option_d": "A general grammar question",
        "answer": "C",
    },
    {
        "slot_number": 14,
        "category": "Device security",
        "question": "You are working from a cafe and need to step away from your laptop for a minute. What should you do?",
        "option_a": "Leave it open if you can still see the table",
        "option_b": "Ask a stranger nearby to watch it",
        "option_c": "Lock the screen and keep the device physically secure",
        "option_d": "Turn down the screen brightness",
        "answer": "C",
    },
    {
        "slot_number": 15,
        "category": "Software updates",
        "question": "Why should employees install approved security updates promptly?",
        "option_a": "Updates only change the appearance of apps",
        "option_b": "Updates often fix vulnerabilities attackers can exploit",
        "option_c": "Updates make passwords unnecessary",
        "option_d": "Updates prevent all phishing emails",
        "answer": "B",
    },
]


def get_db():
    conn = sqlite3.connect(DATABASE_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


def admin_api_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"message": "Unauthorized access."}), 401
        return view_func(*args, **kwargs)
    return wrapped_view


def add_column_if_missing(cursor, table_name, column_name, definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row["name"] for row in cursor.fetchall()}
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def get_risk_level(percentage):
    if percentage >= 80:
        return "Low"
    if percentage >= 50:
        return "Medium"
    return "High"


def setup_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        total_questions INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Active'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        slot_number INTEGER NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        answer TEXT NOT NULL,
        UNIQUE(subject_id, slot_number)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        subject_id INTEGER,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        grade TEXT,
        attempt_number INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    add_column_if_missing(cursor, "questions", "category", "TEXT DEFAULT 'Cybersecurity Awareness'")
    add_column_if_missing(cursor, "students", "company_name", "TEXT DEFAULT ''")
    add_column_if_missing(cursor, "active_students", "company_name", "TEXT DEFAULT ''")
    add_column_if_missing(cursor, "results", "company_name", "TEXT DEFAULT ''")
    add_column_if_missing(cursor, "results", "percentage", "REAL DEFAULT 0")
    add_column_if_missing(cursor, "results", "risk_level", "TEXT DEFAULT ''")
    add_column_if_missing(cursor, "results", "weak_areas", "TEXT DEFAULT '[]'")
    add_column_if_missing(cursor, "results", "breakdown_json", "TEXT DEFAULT '[]'")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        assessment_name TEXT NOT NULL,
        timer_minutes INTEGER NOT NULL DEFAULT 20,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO assessment_settings (id, assessment_name, timer_minutes)
    VALUES (1, ?, 20)
    """, (ASSESSMENT_NAME,))

    cursor.execute("""
    INSERT INTO subjects (id, name, total_questions)
    VALUES (?, ?, ?)
    ON CONFLICT(id)
    DO UPDATE SET
        name = excluded.name,
        total_questions = excluded.total_questions
    """, (ASSESSMENT_ID, ASSESSMENT_NAME, len(CYBER_QUESTIONS)))

    cursor.execute("DELETE FROM subjects WHERE id <> ?", (ASSESSMENT_ID,))

    for item in CYBER_QUESTIONS:
        cursor.execute("""
        INSERT OR IGNORE INTO questions (
            subject_id, slot_number, category, question,
            option_a, option_b, option_c, option_d, answer
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ASSESSMENT_ID,
            item["slot_number"],
            item["category"],
            item["question"],
            item["option_a"],
            item["option_b"],
            item["option_c"],
            item["option_d"],
            item["answer"],
        ))

    cursor.execute("DELETE FROM questions WHERE subject_id <> ?", (ASSESSMENT_ID,))

    cursor.execute("""
    UPDATE subjects
    SET total_questions = (
        SELECT COUNT(*)
        FROM questions
        WHERE subject_id = ?
    )
    WHERE id = ?
    """, (ASSESSMENT_ID, ASSESSMENT_ID))

    conn.commit()
    conn.close()


setup_database()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    error_message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        admins = {
            "Kenny": "1234richard",
            "Taiye": "1234taiye",
            "VIEKBOARD": "Basil404",
        }

        if username in admins and admins[username] == password:
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin"))

        error_message = "Invalid username or password."

    return render_template("login.html", error_message=error_message)


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    return redirect(url_for("login"))


@app.route("/admin")
@admin_required
def admin():
    return render_template(
        "admin.html",
        admin_username=session.get("admin_username", "Admin"),
    )


def get_assessment_settings(cursor):
    cursor.execute("""
    SELECT assessment_name, timer_minutes
    FROM assessment_settings
    WHERE id = 1
    """)
    row = cursor.fetchone()
    if row:
        return dict(row)
    return {"assessment_name": ASSESSMENT_NAME, "timer_minutes": 20}


@app.route("/assessment_questions")
def assessment_questions():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT slot_number, category, question, option_a, option_b, option_c, option_d
    FROM questions
    WHERE subject_id = ?
    ORDER BY slot_number
    """, (ASSESSMENT_ID,))

    questions = [dict(row) for row in cursor.fetchall()]
    settings = get_assessment_settings(cursor)
    conn.close()

    return jsonify({
        "assessment_id": ASSESSMENT_ID,
        "assessment_name": settings["assessment_name"],
        "timer_minutes": settings["timer_minutes"],
        "total_questions": len(questions),
        "questions": questions,
    })


@app.route("/admin_data")
@admin_api_required
def admin_data():
    conn = get_db()
    cursor = conn.cursor()
    settings = get_assessment_settings(cursor)

    cursor.execute("""
    SELECT id, slot_number, category, question, option_a, option_b, option_c,
           option_d, answer
    FROM questions
    WHERE subject_id = ?
    ORDER BY slot_number, id
    """, (ASSESSMENT_ID,))
    questions = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
    SELECT
        id,
        student_name AS employee_name,
        company_name,
        score,
        total,
        percentage,
        risk_level,
        weak_areas,
        attempt_number,
        created_at
    FROM results
    ORDER BY created_at DESC, id DESC
    """)
    results = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
    SELECT a.name, a.company_name, a.started_at, a.status
    FROM active_students a
    ORDER BY a.started_at DESC
    """)
    active_employees = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        "settings": settings,
        "questions": questions,
        "results": results,
        "active_employees": active_employees,
    })


@app.route("/update_settings", methods=["POST"])
@admin_api_required
def update_settings():
    data = request.json or {}
    assessment_name = data.get("assessment_name", "").strip() or ASSESSMENT_NAME

    try:
        timer_minutes = int(data.get("timer_minutes", 20))
    except (TypeError, ValueError):
        return jsonify({"message": "Timer must be a valid number of minutes."}), 400

    if timer_minutes < 1 or timer_minutes > 240:
        return jsonify({"message": "Timer must be between 1 and 240 minutes."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO assessment_settings (id, assessment_name, timer_minutes)
    VALUES (1, ?, ?)
    ON CONFLICT(id)
    DO UPDATE SET
        assessment_name = excluded.assessment_name,
        timer_minutes = excluded.timer_minutes,
        updated_at = CURRENT_TIMESTAMP
    """, (assessment_name, timer_minutes))

    cursor.execute("""
    UPDATE subjects
    SET name = ?
    WHERE id = ?
    """, (assessment_name, ASSESSMENT_ID))

    conn.commit()
    conn.close()

    return jsonify({"message": "Assessment settings saved."})


@app.route("/save_question", methods=["POST"])
@admin_api_required
def save_question():
    data = request.json or {}
    question_id = data.get("id")
    category = data.get("category", "").strip()
    question = data.get("question", "").strip()
    option_a = data.get("option_a", "").strip()
    option_b = data.get("option_b", "").strip()
    option_c = data.get("option_c", "").strip()
    option_d = data.get("option_d", "").strip()
    answer = data.get("answer", "").strip().upper()

    if not all([category, question, option_a, option_b, option_c, option_d, answer]):
        return jsonify({"message": "Please fill all question fields."}), 400

    if answer not in ["A", "B", "C", "D"]:
        return jsonify({"message": "Correct answer must be A, B, C, or D."}), 400

    conn = get_db()
    cursor = conn.cursor()

    if question_id:
        cursor.execute("""
        UPDATE questions
        SET category = ?,
            question = ?,
            option_a = ?,
            option_b = ?,
            option_c = ?,
            option_d = ?,
            answer = ?
        WHERE id = ? AND subject_id = ?
        """, (
            category,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            answer,
            question_id,
            ASSESSMENT_ID,
        ))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Question not found."}), 404
    else:
        cursor.execute("""
        SELECT COALESCE(MAX(slot_number), 0) + 1 AS next_slot
        FROM questions
        WHERE subject_id = ?
        """, (ASSESSMENT_ID,))
        slot_number = cursor.fetchone()["next_slot"]

        cursor.execute("""
        INSERT INTO questions (
            subject_id, slot_number, category, question,
            option_a, option_b, option_c, option_d, answer
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ASSESSMENT_ID,
            slot_number,
            category,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            answer,
        ))

    cursor.execute("""
    UPDATE subjects
    SET total_questions = (
        SELECT COUNT(*)
        FROM questions
        WHERE subject_id = ?
    )
    WHERE id = ?
    """, (ASSESSMENT_ID, ASSESSMENT_ID))

    conn.commit()
    conn.close()

    return jsonify({"message": "Question saved successfully."})


@app.route("/delete_question", methods=["POST"])
@admin_api_required
def delete_question():
    data = request.json or {}
    question_id = data.get("id")

    if not question_id:
        return jsonify({"message": "Question id is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM questions
    WHERE id = ? AND subject_id = ?
    """, (question_id, ASSESSMENT_ID))

    cursor.execute("""
    SELECT id
    FROM questions
    WHERE subject_id = ?
    ORDER BY slot_number, id
    """, (ASSESSMENT_ID,))
    rows = cursor.fetchall()

    for index, row in enumerate(rows, start=1):
        cursor.execute("""
        UPDATE questions
        SET slot_number = ?
        WHERE id = ?
        """, (index, row["id"]))

    cursor.execute("""
    UPDATE subjects
    SET total_questions = ?
    WHERE id = ?
    """, (len(rows), ASSESSMENT_ID))

    conn.commit()
    conn.close()

    return jsonify({"message": "Question deleted successfully."})


@app.route("/save_employee", methods=["POST"])
def save_employee():
    data = request.json or {}
    employee_name = data.get("employee_name", "").strip()
    company_name = data.get("company_name", "").strip()

    if not employee_name:
        return jsonify({"message": "Employee name is required."}), 400

    if not company_name:
        return jsonify({"message": "Company name is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO students (name, company_name)
    VALUES (?, ?)
    ON CONFLICT(name)
    DO UPDATE SET company_name = excluded.company_name
    """, (employee_name, company_name))

    cursor.execute("""
    INSERT INTO active_students (name, company_name, status)
    VALUES (?, ?, 'Active')
    ON CONFLICT(name)
    DO UPDATE SET
        company_name = excluded.company_name,
        started_at = CURRENT_TIMESTAMP,
        status = 'Active'
    """, (employee_name, company_name))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Employee details saved.",
        "employee_name": employee_name,
        "company_name": company_name,
    })


@app.route("/submit_assessment", methods=["POST"])
def submit_assessment():
    data = request.json or {}
    employee_name = data.get("employee_name", "").strip()
    company_name = data.get("company_name", "").strip()
    answers = data.get("answers", {})

    if not employee_name:
        return jsonify({"message": "Employee name is required."}), 400

    if not company_name:
        return jsonify({"message": "Company name is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT slot_number, category, question, option_a, option_b, option_c, option_d, answer
    FROM questions
    WHERE subject_id = ?
    ORDER BY slot_number
    """, (ASSESSMENT_ID,))
    question_rows = cursor.fetchall()

    if not question_rows:
        conn.close()
        return jsonify({"message": "No assessment questions found."}), 400

    score = 0
    breakdown = []
    weak_areas = []

    for row in question_rows:
        slot_key = str(row["slot_number"])
        selected = str(answers.get(slot_key, "")).upper().strip()
        correct = str(row["answer"]).upper().strip()
        is_correct = selected == correct

        if is_correct:
            score += 1
        elif row["category"] not in weak_areas:
            weak_areas.append(row["category"])

        breakdown.append({
            "slot_number": row["slot_number"],
            "category": row["category"],
            "question": row["question"],
            "selected_answer": selected,
            "selected_text": row[f"option_{selected.lower()}"] if selected in ["A", "B", "C", "D"] else "",
            "correct_answer": correct,
            "correct_text": row[f"option_{correct.lower()}"],
            "is_correct": is_correct,
        })

    total = len(question_rows)
    percentage = round((score / total) * 100, 1)
    risk_level = get_risk_level(percentage)

    cursor.execute("""
    INSERT INTO students (name, company_name)
    VALUES (?, ?)
    ON CONFLICT(name)
    DO UPDATE SET company_name = excluded.company_name
    """, (employee_name, company_name))

    cursor.execute("""
    SELECT COALESCE(MAX(attempt_number), 0) AS max_attempt
    FROM results
    WHERE LOWER(student_name) = LOWER(?)
    """, (employee_name,))
    attempt_number = (cursor.fetchone()["max_attempt"] or 0) + 1

    cursor.execute("""
    INSERT INTO results (
        student_name, company_name, subject_id, score, total, grade,
        percentage, risk_level, weak_areas, breakdown_json, attempt_number
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        employee_name,
        company_name,
        ASSESSMENT_ID,
        score,
        total,
        risk_level,
        percentage,
        risk_level,
        json.dumps(weak_areas),
        json.dumps(breakdown),
        attempt_number,
    ))

    cursor.execute("""
    DELETE FROM active_students
    WHERE LOWER(name) = LOWER(?)
    """, (employee_name,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Assessment submitted successfully.",
        "employee_name": employee_name,
        "company_name": company_name,
        "score": score,
        "total": total,
        "percentage": percentage,
        "risk_level": risk_level,
        "weak_areas": weak_areas,
        "breakdown": breakdown,
        "attempt_number": attempt_number,
    })


@app.route("/results")
def results():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        student_name AS employee_name,
        company_name,
        score,
        total,
        percentage,
        risk_level,
        weak_areas,
        attempt_number,
        created_at
    FROM results
    ORDER BY created_at DESC, id DESC
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(rows)


@app.route("/delete_result", methods=["POST"])
@admin_api_required
def delete_result():
    data = request.json or {}
    result_id = data.get("id")

    if not result_id:
        return jsonify({"message": "Result id is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM results WHERE id = ?", (result_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Result deleted successfully."})


# Compatibility endpoints kept lightweight for the existing frontend structure.
@app.route("/available_subjects")
def available_subjects():
    conn = get_db()
    cursor = conn.cursor()
    settings = get_assessment_settings(cursor)
    cursor.execute("SELECT COUNT(*) AS total FROM questions WHERE subject_id = ?", (ASSESSMENT_ID,))
    question_count = cursor.fetchone()["total"]
    conn.close()

    return jsonify([{
        "id": ASSESSMENT_ID,
        "name": settings["assessment_name"],
        "total_questions": question_count,
        "saved_questions": question_count,
    }])


@app.route("/get_questions_by_subject/<int:subject_id>")
def get_questions_by_subject(subject_id):
    if subject_id != ASSESSMENT_ID:
        return jsonify([])

    return assessment_questions()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
