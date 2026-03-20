from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from functools import wraps
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = "kenny_secure_key_1234richard_change_this_later"


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


def calculate_grade(score, total):
    if total <= 0:
        return "F9"

    percentage = (score / total) * 100

    if percentage >= 75:
        return "A1"
    elif percentage >= 70:
        return "B2"
    elif percentage >= 65:
        return "B3"
    elif percentage >= 60:
        return "C4"
    elif percentage >= 55:
        return "C5"
    elif percentage >= 50:
        return "C6"
    elif percentage >= 45:
        return "D7"
    elif percentage >= 40:
        return "E8"
    else:
        return "F9"


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
        subject_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        grade TEXT NOT NULL,
        attempt_number INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    default_subjects = [
        (1, "Subject 1", 40),
        (2, "Subject 2", 40),
        (3, "Subject 3", 40),
        (4, "Subject 4", 60),
        (5, "Subject 5", 40),
        (6, "Subject 6", 40),
        (7, "Subject 7", 60),
        (8, "Subject 8", 40),
        (9, "Subject 9", 40),
    ]

    for subject in default_subjects:
        cursor.execute("""
        INSERT OR IGNORE INTO subjects (id, name, total_questions)
        VALUES (?, ?, ?)
        """, subject)

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
            "Taiye": "1234taiye"
        }

        if username in admins and admins[username] == password:
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin"))
        else:
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
        admin_username=session.get("admin_username", "Admin")
    )


@app.route("/get_subjects")
def get_subjects():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, total_questions
    FROM subjects
    ORDER BY id
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/update_subject_name", methods=["POST"])
@admin_api_required
def update_subject_name():
    data = request.json or {}
    subject_id = data.get("subject_id")
    name = data.get("name", "").strip()

    if not subject_id or not name:
        return jsonify({"message": "Please enter a valid subject name."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE subjects
    SET name = ?
    WHERE id = ?
    """, (name, subject_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Subject name updated successfully."})


@app.route("/save_student", methods=["POST"])
def save_student():
    data = request.json or {}
    student_name = data.get("student_name", "").strip()
    allow_existing = bool(data.get("allow_existing", False))

    if not student_name:
        return jsonify({"message": "Student name is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name
    FROM students
    WHERE LOWER(name) = LOWER(?)
    """, (student_name,))
    existing_student = cursor.fetchone()

    if existing_student:
        canonical_name = existing_student["name"]

        if not allow_existing:
            conn.close()
            return jsonify({
                "message": "This student name already exists.",
                "exists": True,
                "existing_name": canonical_name
            }), 409
    else:
        canonical_name = student_name
        cursor.execute("""
        INSERT INTO students (name)
        VALUES (?)
        """, (canonical_name,))

    cursor.execute("""
    SELECT id
    FROM active_students
    WHERE LOWER(name) = LOWER(?)
    """, (canonical_name,))
    active_row = cursor.fetchone()

    if active_row:
        cursor.execute("""
        UPDATE active_students
        SET started_at = CURRENT_TIMESTAMP,
            status = 'Active'
        WHERE LOWER(name) = LOWER(?)
        """, (canonical_name,))
    else:
        cursor.execute("""
        INSERT INTO active_students (name, status)
        VALUES (?, 'Active')
        """, (canonical_name,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Student name saved successfully.",
        "student_name": canonical_name
    })


@app.route("/get_active_students")
@admin_api_required
def get_active_students():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        a.name,
        a.started_at,
        a.status,
        COALESCE(COUNT(r.id), 0) AS total_attempts
    FROM active_students a
    LEFT JOIN results r
        ON LOWER(r.student_name) = LOWER(a.name)
    GROUP BY a.name, a.started_at, a.status
    ORDER BY a.started_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/save_question", methods=["POST"])
@admin_api_required
def save_question():
    data = request.json or {}

    subject_id = data.get("subject_id")
    slot_number = data.get("slot_number")
    question = data.get("question", "").strip()
    option_a = data.get("option_a", "").strip()
    option_b = data.get("option_b", "").strip()
    option_c = data.get("option_c", "").strip()
    option_d = data.get("option_d", "").strip()
    answer = data.get("answer", "").strip().upper()

    if not all([subject_id, slot_number, question, option_a, option_b, option_c, option_d, answer]):
        return jsonify({"message": "Please fill all question fields."}), 400

    if answer not in ["A", "B", "C", "D"]:
        return jsonify({"message": "Correct answer must be A, B, C, or D."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO questions (
        subject_id, slot_number, question, option_a, option_b, option_c, option_d, answer
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(subject_id, slot_number)
    DO UPDATE SET
        question = excluded.question,
        option_a = excluded.option_a,
        option_b = excluded.option_b,
        option_c = excluded.option_c,
        option_d = excluded.option_d,
        answer = excluded.answer
    """, (
        subject_id,
        slot_number,
        question,
        option_a,
        option_b,
        option_c,
        option_d,
        answer
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": f"Question {slot_number} saved successfully."})


@app.route("/clear_question", methods=["POST"])
@admin_api_required
def clear_question():
    data = request.json or {}
    subject_id = data.get("subject_id")
    slot_number = data.get("slot_number")

    if not subject_id or not slot_number:
        return jsonify({"message": "Invalid question request."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM questions
    WHERE subject_id = ? AND slot_number = ?
    """, (subject_id, slot_number))

    conn.commit()
    conn.close()

    return jsonify({"message": f"Question {slot_number} cleared successfully."})


@app.route("/get_questions_by_subject/<int:subject_id>")
def get_questions_by_subject(subject_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT slot_number, question, option_a, option_b, option_c, option_d, answer
    FROM questions
    WHERE subject_id = ?
    ORDER BY slot_number
    """, (subject_id,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/available_subjects")
def available_subjects():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        s.id,
        s.name,
        s.total_questions,
        COUNT(q.id) AS saved_questions
    FROM subjects s
    JOIN questions q ON s.id = q.subject_id
    GROUP BY s.id, s.name, s.total_questions
    HAVING COUNT(q.id) > 0
    ORDER BY s.id
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/submit_all_subjects", methods=["POST"])
def submit_all_subjects():
    data = request.json or {}
    student_name = data.get("student_name", "").strip()
    all_answers = data.get("all_answers", {})

    if not student_name:
        return jsonify({"message": "Student name is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name
    FROM students
    WHERE LOWER(name) = LOWER(?)
    """, (student_name,))
    student_row = cursor.fetchone()

    canonical_name = student_row["name"] if student_row else student_name

    if not student_row:
        cursor.execute("""
        INSERT INTO students (name)
        VALUES (?)
        """, (canonical_name,))

    cursor.execute("""
    SELECT
        s.id,
        s.name,
        s.total_questions,
        COUNT(q.id) AS saved_questions
    FROM subjects s
    JOIN questions q ON s.id = q.subject_id
    GROUP BY s.id, s.name, s.total_questions
    HAVING COUNT(q.id) > 0
    ORDER BY s.id
    """)
    available_subject_rows = cursor.fetchall()

    if not available_subject_rows:
        conn.close()
        return jsonify({"message": "No available subjects found."}), 400

    summary = []
    grand_score = 0
    grand_total = 0

    for subject in available_subject_rows:
        subject_id = subject["id"]
        subject_name = subject["name"]

        cursor.execute("""
        SELECT slot_number, answer
        FROM questions
        WHERE subject_id = ?
        ORDER BY slot_number
        """, (subject_id,))
        correct_rows = cursor.fetchall()

        subject_answers = all_answers.get(str(subject_id), {})
        score = 0
        total = len(correct_rows)

        for row in correct_rows:
            slot = str(row["slot_number"])
            chosen = str(subject_answers.get(slot, "")).upper().strip()
            correct = str(row["answer"]).upper().strip()

            if chosen == correct:
                score += 1

        grade = calculate_grade(score, total)

        cursor.execute("""
        SELECT COALESCE(MAX(attempt_number), 0) AS max_attempt
        FROM results
        WHERE LOWER(student_name) = LOWER(?) AND subject_id = ?
        """, (canonical_name, subject_id))
        max_attempt_row = cursor.fetchone()
        attempt_number = (max_attempt_row["max_attempt"] or 0) + 1

        cursor.execute("""
        INSERT INTO results (student_name, subject_id, score, total, grade, attempt_number)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (canonical_name, subject_id, score, total, grade, attempt_number))

        summary.append({
            "subject_id": subject_id,
            "subject_name": subject_name,
            "score": score,
            "total": total,
            "grade": grade,
            "attempt_number": attempt_number
        })

        grand_score += score
        grand_total += total

    cursor.execute("""
    DELETE FROM active_students
    WHERE LOWER(name) = LOWER(?)
    """, (canonical_name,))

    conn.commit()
    conn.close()

    grand_grade = calculate_grade(grand_score, grand_total)

    return jsonify({
        "message": "Exam submitted successfully.",
        "student_name": canonical_name,
        "summary": summary,
        "grand_score": grand_score,
        "grand_total": grand_total,
        "grand_grade": grand_grade
    })


@app.route("/get_student_report")
@admin_api_required
def get_student_report():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, total_questions
    FROM subjects
    ORDER BY id
    """)
    subject_rows = cursor.fetchall()
    subjects = [dict(row) for row in subject_rows]

    cursor.execute("""
    SELECT name
    FROM students
    ORDER BY name COLLATE NOCASE
    """)
    student_rows = cursor.fetchall()

    summary_rows = []

    for student_row in student_rows:
        student_name = student_row["name"]

        row_data = {
            "student_name": student_name,
            "subjects": {},
            "grand_score": 0,
            "grand_total": 0,
            "total_attempt_records": 0
        }

        for subject in subjects:
            cursor.execute("""
            SELECT score, total, grade, attempt_number, created_at
            FROM results
            WHERE LOWER(student_name) = LOWER(?) AND subject_id = ?
            ORDER BY attempt_number DESC, id DESC
            LIMIT 1
            """, (student_name, subject["id"]))
            latest = cursor.fetchone()

            cursor.execute("""
            SELECT COUNT(*) AS total_attempts
            FROM results
            WHERE LOWER(student_name) = LOWER(?) AND subject_id = ?
            """, (student_name, subject["id"]))
            count_row = cursor.fetchone()
            subject_attempt_count = count_row["total_attempts"]

            if latest:
                latest_score = latest["score"]
                latest_total = latest["total"]
                latest_grade = latest["grade"]
                latest_attempt = latest["attempt_number"]
            else:
                latest_score = 0
                latest_total = 0
                latest_grade = "-"
                latest_attempt = 0

            row_data["subjects"][str(subject["id"])] = {
                "subject_name": subject["name"],
                "score": latest_score,
                "total": latest_total,
                "grade": latest_grade,
                "latest_attempt": latest_attempt,
                "attempt_count": subject_attempt_count,
                "max_questions": subject["total_questions"]
            }

            row_data["grand_score"] += latest_score
            row_data["grand_total"] += latest_total
            row_data["total_attempt_records"] += subject_attempt_count

        row_data["grand_grade"] = calculate_grade(
            row_data["grand_score"],
            row_data["grand_total"]
        )

        summary_rows.append(row_data)

    cursor.execute("""
    SELECT
        r.id,
        r.student_name,
        s.name AS subject_name,
        r.score,
        r.total,
        r.grade,
        r.attempt_number,
        r.created_at
    FROM results r
    JOIN subjects s ON r.subject_id = s.id
    ORDER BY r.created_at DESC, r.id DESC
    """)
    attempt_rows = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        "subjects": subjects,
        "students": summary_rows,
        "attempts": attempt_rows
    })


@app.route("/delete_student", methods=["POST"])
@admin_api_required
def delete_student():
    data = request.json or {}
    student_name = data.get("student_name", "").strip()

    if not student_name:
        return jsonify({"message": "Student name is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM results
    WHERE LOWER(student_name) = LOWER(?)
    """, (student_name,))

    cursor.execute("""
    DELETE FROM active_students
    WHERE LOWER(name) = LOWER(?)
    """, (student_name,))

    cursor.execute("""
    DELETE FROM students
    WHERE LOWER(name) = LOWER(?)
    """, (student_name,))

    conn.commit()
    conn.close()

    return jsonify({"message": f"{student_name} deleted successfully."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)