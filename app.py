from flask import Flask, render_template, request, redirect, session
import sqlite3
import cv2
import os
import numpy as np
from datetime import datetime

app = Flask(__name__)
app.secret_key="attendance"


@app.route('/')
def home():
    return render_template("home.html")


@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM teachers
        WHERE username=? AND password=?
        """,(username,password))

        teacher = cursor.fetchone()

        conn.close()

        if teacher:

            session['teacher_id'] = teacher[0]
            session['teacher_name'] = teacher[1]

            return redirect('/dashboard')

        return "Invalid Login"

    return render_template("login.html")


@app.route('/dashboard')
def dashboard():

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
    """,(teacher_id,))

    classes = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        classes=classes,
        teacher_name=teacher_name
    )



# CREATE CLASS PAGE
@app.route('/create_class', methods=['POST'])
def create_class():

    class_name = request.form['class_name']
    subject = request.form['subject']

    teacher_id = session['teacher_id']

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO classes(
        class_name,
        subject,
        teacher_id
    )
    VALUES(?,?,?)
    """,(class_name,subject,teacher_id))

    conn.commit()
    conn.close()

    return redirect('/dashboard')



# REGISTER STUDENT PAGE
@app.route('/register_student', methods=['GET', 'POST'])
def register_student():

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

        return redirect('/dashboard')

    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()

    conn.close()

    return render_template(
        'register_student.html',
        classes=classes
    )





@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')



# @app.route('/register_face_page', methods=['GET','POST'])
# def register_face():

#     if request.method == 'POST':

#         student_name = request.form['student_name']

#         import cv2, os

#         path = os.path.join("dataset", student_name)

#         os.makedirs(path, exist_ok=True)

#         cam = cv2.VideoCapture(0)

#         detector = cv2.CascadeClassifier(
#             cv2.data.haarcascades +
#             'haarcascade_frontalface_default.xml'
#         )

#         count = 0

#         while True:

#             ret, frame = cam.read()

#             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

#             faces = detector.detectMultiScale(gray,1.3,5)

#             for (x,y,w,h) in faces:

#                 count += 1

#                 cv2.imwrite(
#                     f"{path}/{count}.jpg",
#                     gray[y:y+h,x:x+w]
#                 )

#                 cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)

#             cv2.imshow("Register Face",frame)

#             if cv2.waitKey(1)==13 or count>=20:
#                 break

#         cam.release()
#         cv2.destroyAllWindows()

#         return "Face Registered Successfully"

#     return render_template("register_face.html")

@app.route('/register_face_page')
def register_face_page():
    return redirect('/camera')

@app.route('/register_face', methods=['POST'])
def register_face():

    name = request.form['student_name']

    return f"{name} Face Registration Started"




@app.route('/train_model')
def train_model():

    faces = []
    labels = []

    dataset_path = "dataset"

    if not os.path.exists(dataset_path):
        os.makedirs(dataset_path)
        return "Dataset folder created. Add faces first."


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

            img = cv2.resize(img, (200,200))

            faces.append(img)
            labels.append(current_label)

        current_label += 1


    recognizer = cv2.face.LBPHFaceRecognizer_create()

    recognizer.train(faces, np.array(labels))

    recognizer.save("face_model.yml")


    with open("labels.txt","w") as f:

        for label,name in label_map.items():
            f.write(f"{label},{name}\n")


    return "Model Trained Successfully!"


@app.route('/take_attendance/<int:class_id>')
def take_attendance(class_id):

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("face_model.yml")

    labels = {}

    with open("labels.txt","r") as f:
        for line in f:
            label,name=line.strip().split(",")
            labels[int(label)] = name


    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT student_name FROM students WHERE class_id=?",
        (class_id,)
    )

    class_students = [row[0] for row in cursor.fetchall()]

    conn.close()


    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades+'haarcascade_frontalface_default.xml'
    )

    cap = cv2.VideoCapture(0)

    marked_students=[]

    while True:

        ret, frame = cap.read()

        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray,1.3,5)

        for (x,y,w,h) in faces:

            face = gray[y:y+h,x:x+w]

            face = cv2.resize(face,(200,200))

            label,confidence = recognizer.predict(face)

            if confidence < 70:

                name = labels[label]

                # ONLY CLASS STUDENTS ALLOWED
                if name in class_students:

                    cv2.putText(
                        frame,
                        f"{name} Present",
                        (x,y-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0,255,0),
                        2
                    )

                    if name not in marked_students:

                        now=datetime.now()

                        date=now.strftime("%Y-%m-%d")
                        time=now.strftime("%H:%M:%S")

                        conn=sqlite3.connect("attendance.db")
                        cursor=conn.cursor()

                        cursor.execute("""
                        INSERT INTO attendance(
                        student_name,
                        date,
                        time,
                        status
                        ) VALUES(?,?,?,?)
                        """,(name,date,time,"Present"))

                        conn.commit()
                        conn.close()

                        marked_students.append(name)

                else:

                    cv2.putText(
                        frame,
                        "Not In This Class",
                        (x,y-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0,0,255),
                        2
                    )

            cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)

        cv2.imshow("Class Attendance",frame)

        if cv2.waitKey(1)==ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    return "Attendance Completed!"




@app.route('/view_students/<int:class_id>')
def view_students(class_id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE class_id=?
    """,(class_id,))

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "class_students.html",
        students=students
    )


@app.route('/register_teacher', methods=['GET','POST'])
def register_teacher():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO teachers(username,password)
        VALUES(?,?)
        """,(username,password))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("register_teacher.html")



@app.route('/profile')
def profile():

    if 'teacher_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username FROM teachers
    WHERE id=?
    """,(session['teacher_id'],))

    teacher = cursor.fetchone()

    conn.close()

    return render_template(
        "profile.html",
        teacher=teacher
    )

@app.route('/change_password', methods=['GET','POST'])
def change_password():

    if request.method == 'POST':

        new_password = request.form['password']

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE teachers
        SET password=?
        WHERE id=?
        """,(new_password,session['teacher_id']))

        conn.commit()
        conn.close()

        return redirect('/profile')

    return render_template("change_password.html")

@app.route('/delete_class/<int:id>')
def delete_class(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM classes WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')




@app.route('/delete_student/<int:id>')
def delete_student(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM students WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')

@app.route('/create_class', methods=['GET'])
def create_class_page():
    return render_template("create_class.html")


@app.route('/reports')
def reports():

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT attendance.date,
               students.student_name,
               students.roll_no
        FROM attendance
        JOIN students
        ON attendance.student_name = students.student_name
        ORDER BY attendance.date DESC
    """)

    data = cursor.fetchall()

    conn.close()

    grouped_data = {}

    for row in data:

        date = row[0]

        if date not in grouped_data:
            grouped_data[date] = []

        grouped_data[date].append({
            "name": row[1],
            "roll": row[2]
        })

    return render_template(
        "reports.html",
        grouped_data=grouped_data
    )

@app.route('/camera')
def camera():
    return render_template("camera.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)