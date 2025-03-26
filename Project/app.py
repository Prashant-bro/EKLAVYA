from flask import Flask, render_template, request, redirect, url_for, flash,session
import mysql.connector as mc
import threading
import webbrowser
import pyautogui
import cv2 as c
from tkinter import messagebox as m
import easyocr as eo
import mediapipe as mp

def con():
    try:
        return mc.connect(
            host="localhost",
            user="root",
            password="5867",
            database="eklavya",
            charset="latin1"
        )
    except mc.Error as e:
        m.showerror("Database Error", f"Connection failed: {str(e)}")
        return None

def cam1():
    cam = c.VideoCapture(0)
    if not cam.isOpened():
        m.showerror("Error", "Cam couldn't be opened")
        return

    while True:
        ret, frame = cam.read()
        if not ret:
            m.showerror("Error", "Failed to capture frame")
            continue

        c.imshow('Live Camera - Press "s" to scan | Press "ESC" to exit', frame)
        key = c.waitKey(1) & 0xFF

        if key == ord('s'):
            if easy(frame):
                if irismatc(frame):
                    webbrowser.open("http://127.0.0.1:5000/")
                    threading.Timer(1.0, close_browser).start()
                else:
                    m.showerror("Error", "Iris scan failed. Try again.")

        elif key == 27:
            break

    cam.release()
    c.destroyAllWindows()

def easy(frame):
    try:
        reader = eo.Reader(['en'])
        gray_frame = c.cvtColor(frame, c.COLOR_BGR2GRAY)  
        results = reader.readtext(gray_frame)
        for text in results:
            if len(text[1]) == 10 and text[1].isalnum():
                m.showinfo("Detected", "Data found! Proceeding for iris scan...")
                if check(text[1]):
                    return True
    except Exception as e:
        m.showerror("Error", f"OCR Failed: {str(e)}")
    return False

def check(voter_id):
    db = con()
    if not db:
        return False

    try:
        cur = db.cursor()
        query = "SELECT has_voted FROM voters WHERE voter_id = %s"
        cur.execute(query, (voter_id,))
        result = cur.fetchone()
        if result:
            if result[0]:
                m.showerror("Error", "Already voted!")
            else:
                m.showinfo("Proceed", "Proceeding for iris scan...")
                return True
        else:
            m.showerror("Error", "Voter ID not found in the database")
    except mc.Error as e:
        m.showerror("Database Error", str(e))
    finally:
        cur.close()
        db.close()
    return False

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

def irismatc(frame):
    try:
        rgb_frame = c.cvtColor(frame, c.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            iris_array = []
            for face_landmarks in results.multi_face_landmarks:
                iris_landmarks = [face_landmarks.landmark[i] for i in range(468, 478)]
                iris_array = [(int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0])) for landmark in iris_landmarks]

            db = con()
            if not db:
                return False

            try:
                cur = db.cursor()
                query = "SELECT iris_array FROM voters WHERE iris_array = %s"
                cur.execute(query, (str(iris_array),))
                result = cur.fetchone()

                if result:
                    m.showinfo("Success", "Iris scan successful. Voter verified!")
                    return True
                else:
                    m.showerror("Error", "Iris data not found in the database")
                    return False
            finally:
                cur.close()
                db.close()
        else:
            m.showerror("Error", "Iris not detected. Try again.")
            return False
    except Exception as e:
        m.showerror("Error", f"Iris scan failed: {str(e)}")
        return False

def start_flask():
    flask_app = Flask(__name__)
    flask_app.secret_key = "my_super_secret_key"
    db = con()
    if not db:
        return

    @flask_app.route('/', methods=["GET", "POST"])
    def home():
        if request.method == "POST":
            selected_option = request.form['option']
            voter_id = request.form.get('voter_id')  

            db = con()
            if not db:
                return redirect(url_for('home'))

            try:
                cursor = db.cursor()

            
                cursor.execute("SELECT has_voted FROM users WHERE voter_id = %s", (voter_id,))
                result = cursor.fetchone()

                if result and result[0] == 1:
                    flash("You have already voted. Duplicate votes are not allowed!", "error")
                else:
                
                    query = "UPDATE votes SET vote_count = vote_count + 1 WHERE candidate = %s"
                    cursor.execute(query, (selected_option,))

                    cursor.execute("UPDATE users SET has_voted = 1 WHERE voter_id = %s", (voter_id,))
                    db.commit()

                    flash(f"Vote for '{selected_option}' recorded successfully!", "success")
                    threading.Timer(1.0, close_browser).start()
            except mc.Error as e:
                flash(f"Database Error: {str(e)}", "error")
            finally:
                cursor.close()
                db.close()

            return redirect(url_for('home'))

        return render_template('vote.html',voter_id=session.get('voter_id'))


    flask_app.run(debug=True, use_reloader=False)

def close_browser():
    pyautogui.hotkey('ctrl', 'w')

threading.Thread(target=start_flask, daemon=True).start()

cam1()
