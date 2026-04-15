from flask import Flask, render_template, request, redirect, session
import sqlite3
import cv2
import os
import numpy as np
from datetime import datetime
import base64

app = Flask(__name__)
app.secret_key = "attendance"


# ================= HOME =================
@app.route('/')
def home():
    return render_template("home.html")


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM teachers
        WHERE username=? AND password=?
        """, (username, password))

        teacher = cursor.fetchone()
        conn.close()

        if teacher:
            session['teacher_id'] = teacher[0]
            session['teacher_name'] = teacher[1]
            return redirect('/dashboard')

        return "Invalid Login"

    return render_template("login.html")


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if 'teacher_id' not in session:
        return redirect('/login')

    teacher_id = session['teacher_id']
    teacher_name = session['teacher_name']

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT classes.id,
           classes.class_name,
           classes.subject,
           COUNT(students.id)
    FROM classes
    LEFT JOIN students
    ON classes.id = students.class_id
    WHERE classes.teacher_id=?
    GROUP BY classes.id
    """, (teacher_id,))

    classes = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        classes=classes,
        teacher_name=teacher_name
    )


# ================= CREATE CLASS =================
@app.route('/create_class', methods=['GET', 'POST'])
def create_class():

    if 'teacher_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        class_name = request.form['class_name']
        subject = request.form['subject']
        teacher_id = session['teacher_id']

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO classes(class_name, subject, teacher_id)
        VALUES(?,?,?)
        """, (class_name, subject, teacher_id))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template("create_class.html")


# ================= REGISTER STUDENT =================
@app.route('/register_student', methods=['GET', 'POST'])
def register_student():

    if 'teacher_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    if request.method == 'POST':

        student_name = request.form['student_name']
        roll_no = request.form['roll_no']
        class_id = request.form['class_id']

        cursor.execute("""
        INSERT INTO students(student_name, roll_no, class_id)
        VALUES(?,?,?)
        """, (student_name, roll_no, class_id))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    cursor.execute("""
    SELECT * FROM classes
    WHERE teacher_id=?
    """, (session['teacher_id'],))

    classes = cursor.fetchall()

    conn.close()

    return render_template("register_student.html", classes=classes)


# ================= REGISTER TEACHER =================
@app.route('/register_teacher', methods=['GET', 'POST'])
def register_teacher():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO teachers(username,password)
        VALUES(?,?)
        """, (username, password))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("register_teacher.html")


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ================= FACE REGISTRATION =================
@app.route('/register_face_page')
def register_face_page():
    return render_template("camera.html")


@app.route('/save_face', methods=['POST'])
def save_face():

    student_name = request.form['student_name']
    image_data = request.form['image']

    image_data = image_data.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    folder_path = f"dataset/{student_name}"
    os.makedirs(folder_path, exist_ok=True)

    image_number = len(os.listdir(folder_path)) + 1

    with open(f"{folder_path}/{image_number}.jpg", "wb") as f:
        f.write(image_bytes)

    return "Face Saved Successfully!"


# ================= TRAIN MODEL =================
@app.route('/train_model')
def train_model():

    faces = []
    labels = []

    dataset_path = "dataset"

    if not os.path.exists(dataset_path):
        return "Dataset Folder Missing"

    label_map = {}
    current_label = 0

    for student_name in os.listdir(dataset_path):

        student_folder = os.path.join(dataset_path, student_name)

        if not os.path.isdir(student_folder):
            continue

        label_map[current_label] = student_name

        for image_name in os.listdir(student_folder):

            img_path = os.path.join(student_folder, image_name)

            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

            if img is None:
                continue

            img = cv2.resize(img, (200, 200))

            faces.append(img)
            labels.append(current_label)

        current_label += 1

    if len(faces) == 0:
        return "No Face Images Found"

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    recognizer.train(faces, np.array(labels))
    recognizer.save("face_model.yml")

    with open("labels.txt", "w") as f:
        for label, name in label_map.items():
            f.write(f"{label},{name}\n")

    return "Model Trained Successfully"


# ================= TAKE ATTENDANCE =================
# @app.route('/take_attendance/<int:class_id>')
# def take_attendance(class_id):

#     conn = sqlite3.connect("attendance.db")
#     cursor = conn.cursor()

#     cursor.execute("""
#     SELECT student_name, roll_no
#     FROM students
#     WHERE class_id=?
#     """, (class_id,))

#     students = cursor.fetchall()

#     conn.close()

#     return render_template(
#         'attendance_camera.html',
#         class_id=class_id,
#         students=students
#     )

# @app.route('/take_attendance/<int:class_id>')
# def take_attendance(class_id):

#     recognizer = cv2.face.LBPHFaceRecognizer_create()
#     recognizer.read("face_model.yml")

#     labels = {}

#     with open("labels.txt", "r") as f:
#         for line in f:
#             label, name = line.strip().split(",")
#             labels[int(label)] = name

#     conn = sqlite3.connect("attendance.db")
#     cursor = conn.cursor()

#     cursor.execute("""
#     SELECT student_name
#     FROM students
#     WHERE class_id=?
#     """, (class_id,))

#     class_students = [row[0] for row in cursor.fetchall()]

#     face_cascade = cv2.CascadeClassifier(
#         cv2.data.haarcascades +
#         'haarcascade_frontalface_default.xml'
#     )

#     cap = cv2.VideoCapture(0)

#     marked_students = []

#     while True:

#         ret, frame = cap.read()

#         gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

#         faces = face_cascade.detectMultiScale(gray, 1.3, 5)

#         for (x, y, w, h) in faces:

#             face = gray[y:y+h, x:x+w]
#             face = cv2.resize(face, (200, 200))

#             label, confidence = recognizer.predict(face)

#             if confidence < 70:

#                 name = labels[label]

#                 if name in class_students:

#                     if name not in marked_students:

#                         now = datetime.now()

#                         date = now.strftime("%Y-%m-%d")
#                         time = now.strftime("%H:%M:%S")

#                         cursor.execute("""
#                         SELECT * FROM attendance
#                         WHERE student_name=? AND date=?
#                         """, (name, date))

#                         existing = cursor.fetchone()

#                         if not existing:

#                             cursor.execute("""
#                             INSERT INTO attendance(student_name,date,time,status)
#                             VALUES(?,?,?,?)
#                             """, (name, date, time, "Present"))

#                             conn.commit()

#                         marked_students.append(name)

#                     cv2.putText(
#                         frame,
#                         f"{name} Present",
#                         (x, y-10),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         0.8,
#                         (0,255,0),
#                         2
#                     )

#             cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)

#         cv2.imshow("Attendance", frame)

#         if cv2.waitKey(1) == ord('q'):
#             break

#     cap.release()
#     conn.close()
#     cv2.destroyAllWindows()

#     return "Attendance Completed"



@app.route('/take_attendance/<int:class_id>')
def take_attendance(class_id):

    return render_template(
        "attendance_camera.html",
        class_id=class_id
    )


# ================= MARK ATTENDANCE =================
@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():

    student_name = request.form['student_name']

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM attendance
    WHERE student_name=? AND date=?
    """, (student_name, date))

    existing = cursor.fetchone()

    if existing:
        conn.close()
        return "Attendance Already Marked"

    cursor.execute("""
    INSERT INTO attendance(student_name,date,time,status)
    VALUES(?,?,?,?)
    """, (student_name, date, time, "Present"))

    conn.commit()
    conn.close()

    return "Attendance Marked Successfully"


# ================= REPORTS =================
@app.route('/reports')
def reports():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT student_name,date,time,status
    FROM attendance
    ORDER BY date DESC,time DESC
    """)

    records = cursor.fetchall()

    conn.close()

    return render_template("reports.html", records=records)


# ================= VIEW STUDENTS =================
# @app.route('/view_students/<int:class_id>')
# def view_students(class_id):

#     conn = sqlite3.connect("attendance.db")
#     cursor = conn.cursor()

#     cursor.execute("""
#     SELECT * FROM students
#     WHERE class_id=?
#     """, (class_id,))

#     students = cursor.fetchall()

#     conn.close()

#     return render_template("view_students.html", students=students)

@app.route('/view_students/<int:class_id>')
def view_students(class_id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, student_name, roll_no
    FROM students
    WHERE class_id=?
    """, (class_id,))

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "view_students.html",
        students=students
    )


# ================= STUDENT ATTENDANCE =================
@app.route('/student_attendance/<int:student_id>')
def student_attendance(student_id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT student_name, roll_no
    FROM students
    WHERE id=?
    """, (student_id,))

    student = cursor.fetchone()

    if not student:
        return "Student Not Found"

    student_name = student[0]
    roll_no = student[1]

    cursor.execute("""
    SELECT COUNT(*)
    FROM attendance
    WHERE student_name=?
    """, (student_name,))

    present_days = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(DISTINCT date)
    FROM attendance
    """)

    total_days = cursor.fetchone()[0]

    percentage = 0 if total_days == 0 else round((present_days / total_days) * 100, 2)

    conn.close()

    return render_template(
        "student_attendance.html",
        student_name=student_name,
        roll_no=roll_no,
        present_days=present_days,
        total_days=total_days,
        percentage=percentage
    )


# ================= PROFILE =================
@app.route('/profile')
def profile():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username FROM teachers
    WHERE id=?
    """, (session['teacher_id'],))

    teacher = cursor.fetchone()

    conn.close()

    return render_template("profile.html", teacher=teacher)


# ================= CHANGE PASSWORD =================
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():

    if request.method == 'POST':

        new_password = request.form['password']

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE teachers
        SET password=?
        WHERE id=?
        """, (new_password, session['teacher_id']))

        conn.commit()
        conn.close()

        return redirect('/profile')

    return render_template("change_password.html")


# ================= DELETE CLASS =================
@app.route('/delete_class/<int:id>')
def delete_class(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE class_id=?", (id,))
    cursor.execute("DELETE FROM classes WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/dashboard')


# ================= DELETE STUDENT =================
@app.route('/delete_student/<int:id>')
def delete_student(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/dashboard')


# ================= CAMERA =================
@app.route('/camera')
def camera():
    return render_template("camera.html")

import json


@app.route('/scan_attendance', methods=['POST'])
def scan_attendance():

    data = request.get_json()

    image_data = data['image']
    class_id = data['class_id']

    image_data = image_data.split(",")[1]

    image_bytes = base64.b64decode(image_data)

    np_arr = np.frombuffer(image_bytes, np.uint8)

    img = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)


    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("face_model.yml")


    labels = {}

    with open("labels.txt","r") as f:
        for line in f:
            label,name = line.strip().split(",")
            labels[int(label)] = name


    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        'haarcascade_frontalface_default.xml'
    )


    faces = face_cascade.detectMultiScale(img,1.3,5)


    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT student_name
    FROM students
    WHERE class_id=?
    """,(class_id,))

    class_students = [row[0] for row in cursor.fetchall()]


    for (x,y,w,h) in faces:

        face = img[y:y+h,x:x+w]

        face = cv2.resize(face,(200,200))

        label,confidence = recognizer.predict(face)

        if confidence < 70:

            name = labels[label]

            if name in class_students:

                now = datetime.now()

                date = now.strftime("%Y-%m-%d")
                time = now.strftime("%H:%M:%S")

                cursor.execute("""
                SELECT * FROM attendance
                WHERE student_name=? AND date=?
                """,(name,date))

                existing = cursor.fetchone()

                if existing:
                    conn.close()
                    return f"{name} Already Marked Today"

                cursor.execute("""
                INSERT INTO attendance(student_name,date,time,status)
                VALUES(?,?,?,?)
                """,(name,date,time,"Present"))

                conn.commit()
                conn.close()

                return f"{name} Attendance Marked Successfully"

    conn.close()

    return "Face Not Recognized"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)