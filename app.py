from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = "kenny_secure_key_1234richard_change_this_later"


def get_db():
    conn = sqlite3.connect("database.db")
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
        name TEXT NOT NULL UNIQUE
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
        UNIQUE(student_name, subject_id)
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
    return render_template("admin.html", admin_username=session.get("admin_username", "Admin"))


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
    data = request.json
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
    data = request.json
    student_name = data.get("student_name", "").strip()

    if not student_name:
        return jsonify({"message": "Student name is required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR IGNORE INTO students (name)
    VALUES (?)
    """, (student_name,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Student name saved successfully."})


@app.route("/save_question", methods=["POST"])
@admin_api_required
def save_question():
    data = request.json

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
    data = request.json
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


@app.route("/submit_exam", methods=["POST"])
def submit_exam():
    data = request.json
    subject_id = data.get("subject_id")
    student_name = data.get("student_name", "").strip()
    answers = data.get("answers", {})

    if not student_name:
        return jsonify({"message": "Student name is required."}), 400

    if not subject_id:
        return jsonify({"message": "Subject is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO students (name)
    VALUES (?)
    """, (student_name,))

    cursor.execute("""
    SELECT slot_number, answer
    FROM questions
    WHERE subject_id = ?
    ORDER BY slot_number
    """, (subject_id,))
    correct_rows = cursor.fetchall()

    score = 0
    total = len(correct_rows)

    for row in correct_rows:
        slot = str(row["slot_number"])
        if slot in answers and answers[slot] == row["answer"]:
            score += 1

    cursor.execute("""
    INSERT INTO results (student_name, subject_id, score, total)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(student_name, subject_id)
    DO UPDATE SET
        score = excluded.score,
        total = excluded.total
    """, (student_name, subject_id, score, total))

    conn.commit()
    conn.close()

    return jsonify({
        "score": score,
        "total": total
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

    report = []

    for student_row in student_rows:
        student_name = student_row["name"]

        student_entry = {
            "student_name": student_name,
            "subjects": {},
            "grand_score": 0,
            "grand_total": 0
        }

        for subject in subjects:
            cursor.execute("""
            SELECT score, total
            FROM results
            WHERE student_name = ? AND subject_id = ?
            """, (student_name, subject["id"]))
            result = cursor.fetchone()

            if result:
                score = result["score"]
                total = result["total"]
            else:
                score = 0
                total = 0

            student_entry["subjects"][str(subject["id"])] = {
                "subject_name": subject["name"],
                "score": score,
                "total": total,
                "max_questions": subject["total_questions"]
            }

            student_entry["grand_score"] += score
            student_entry["grand_total"] += total

        report.append(student_entry)

    conn.close()

    return jsonify({
        "subjects": subjects,
        "students": report
    })


import os

if __name__ == "__main__":
    setup_database()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)