import os
import shutil

# Delete DB
if os.path.exists("attendance.db"):
    os.remove("attendance.db")

# Delete model files
if os.path.exists("face_model.yml"):
    os.remove("face_model.yml")

if os.path.exists("labels.txt"):
    os.remove("labels.txt")

# Delete dataset folder
if os.path.exists("dataset"):
    shutil.rmtree("dataset")

print("System Reset Complete")