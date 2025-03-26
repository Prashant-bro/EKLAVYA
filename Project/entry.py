import cv2 as cv
import mediapipe as mp
import easyocr as eo
import mysql.connector as mc
from tkinter import messagebox as m

def con():
    try:
        return mc.connect(
            host="localhost",
            user="root",
            database="eklavya",
            passwd="5867",
            charset="latin1"
        )
    except mc.Error as e:
        m.showerror("Database Error", f"Connection failed: {str(e)}")
        return None

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

def iris(frame):
    rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        iris_array = []
        for face_landmarks in results.multi_face_landmarks:
            iris_landmarks = [face_landmarks.landmark[i] for i in range(468, 478)]
            iris_array = [(int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0])) for landmark in iris_landmarks]
        return iris_array  
    return None

def easy(frame):
    try:
        reader = eo.Reader(['en'])
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)  
        result = reader.readtext(gray_frame)

        for text in result:
            if len(text[1]) == 10 and text[1].isalnum():
                return text[1]
    except Exception as e:
        m.showerror("Error", f"OCR failed: {str(e)}")
    return None

def Entry(voter_id, iris_array):
    db = con()
    if not db:
        return

    try:
        cur = db.cursor()
        query = "INSERT INTO users (voter_id, iris_array) VALUES (%s, %s)"
        values = (voter_id, str(iris_array))  
        cur.execute(query, values)
        db.commit()
        m.showinfo("Info", "Entry successfully recorded!")
    except mc.Error as err:
        m.showerror("Error", f"Database Error: {err}")
    finally:
        cur.close()
        db.close()

def cam():
    video_cap = cv.VideoCapture(0)
    if not video_cap.isOpened():
        m.showerror("Error", "Could not open camera!")
        return

    while True:
        ret, video_data = video_cap.read()
        if not ret:
            m.showerror("Error", "Failed to capture frame.")
            continue

        cv.imshow("Live Camera - Press 's' to scan | 'ESC' to exit", video_data)
        key = cv.waitKey(10) & 0xFF

        if key == ord('s'):
            voter_id = easy(video_data)
            iris_data = iris(video_data)
            if voter_id and iris_data:
                Entry(voter_id, iris_data)
            else:
                m.showwarning("Warning", "Failed to capture voter ID or iris data. Try again.")

        elif key == 27:  
            break  

    video_cap.release()
    cv.destroyAllWindows()

while True:
    cam()
