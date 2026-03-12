from flask import Flask, render_template, request
import os
import cv2
import numpy as np
import piexif
import joblib
import pickle
from PIL import Image, ImageChops, ImageEnhance

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
ELA_FOLDER = "static/ela_images"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ELA_FOLDER"] = ELA_FOLDER

# Load ML model
model = joblib.load("tampering_detector.pkl")
scaler = pickle.load(open("scaler.pkl", "rb"))

# -------------------------
# ELA GENERATION
# -------------------------
def generate_ela(image_path):

    temp_path = "temp.jpg"

    image = Image.open(image_path).convert("RGB")
    image.save(temp_path, "JPEG", quality=90)

    compressed = Image.open(temp_path)

    ela_image = ImageChops.difference(image, compressed)

    extrema = ela_image.getextrema()
    max_diff = max([ex[1] for ex in extrema])

    scale = 255.0 / max_diff if max_diff != 0 else 1

    ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)

    ela_path = os.path.join(ELA_FOLDER, os.path.basename(image_path))
    ela_image.save(ela_path)

    return ela_path


# -------------------------
# TAMPER REGION DETECTION
# -------------------------
def highlight_tampering(ela_path):

    img = cv2.imread(ela_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:

        if cv2.contourArea(cnt) > 300:

            x, y, w, h = cv2.boundingRect(cnt)

            cv2.rectangle(img, (x, y), (x+w, y+h), (0,0,255), 2)

    result_path = ela_path.replace(".jpg", "_tamper.jpg")

    cv2.imwrite(result_path, img)

    return result_path


# -------------------------
# FEATURE EXTRACTION
# -------------------------
def extract_features(image_path):

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    focal_length = 0
    iso = 0
    exposure_time = 0
    aperture = 0
    orientation = 0

    try:
        exif_dict = piexif.load(image_path)

        if piexif.ExifIFD.FocalLength in exif_dict["Exif"]:
            focal_length = exif_dict["Exif"][piexif.ExifIFD.FocalLength][0]

        if piexif.ExifIFD.ISOSpeedRatings in exif_dict["Exif"]:
            iso = exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings]

        if piexif.ExifIFD.ExposureTime in exif_dict["Exif"]:
            exposure_time = exif_dict["Exif"][piexif.ExifIFD.ExposureTime][0]

        if piexif.ExifIFD.FNumber in exif_dict["Exif"]:
            aperture = exif_dict["Exif"][piexif.ExifIFD.FNumber][0]

        if piexif.ImageIFD.Orientation in exif_dict["0th"]:
            orientation = exif_dict["0th"][piexif.ImageIFD.Orientation]

    except:
        pass

    gray = np.float32(gray) / 255.0

    dct = cv2.dct(gray)

    dct_mean = np.mean(dct)
    dct_std = np.std(dct)

    blur = cv2.GaussianBlur(gray, (5,5), 0)

    noise = gray - blur

    noise_mean = np.mean(noise)
    noise_std = np.std(noise)

    patches = []
    h, w = gray.shape

    for i in range(0, h-32, 32):
        for j in range(0, w-32, 32):

            patch = gray[i:i+32, j:j+32]

            patches.append(np.mean(patch))

    patch_mean = np.mean(patches) if len(patches) > 0 else 0

    features = np.array([
        focal_length,
        iso,
        exposure_time,
        aperture,
        orientation,
        dct_mean,
        noise_mean,
        patch_mean,
        dct_std,
        noise_std
    ])

    # pad to match training features (36)
    features = np.pad(features, (0, 36 - len(features)), 'constant')

    return features.reshape(1,-1)


# -------------------------
# HOME PAGE
# -------------------------
@app.route("/")
def home():
    return render_template("index-apple.html")


# -------------------------
# PREDICT
# -------------------------
@app.route("/predict", methods=["POST"])
def predict():

    file = request.files["image"]

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)

    file.save(filepath)

    ela_path = generate_ela(filepath)

    features = extract_features(filepath)

    features = scaler.transform(features)

    prediction = model.predict(features)

    result = "Tampered Image" if prediction == 1 else "Authentic Image"

    if prediction == 1:
        tamper_path = highlight_tampering(ela_path)
    else:
        tamper_path = ela_path

    return render_template(\n    "result-apple.html",\n    prediction=result,\n    img_path=filepath,\n    ela_path=ela_path,\n    tamper_path=tamper_path\n)


if __name__ == "__main__":
    app.run(debug=True)