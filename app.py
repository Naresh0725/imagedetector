from flask import Flask, render_template, request
import os
import cv2
import numpy as np
import piexif
import joblib
import pickle
from PIL import Image, ImageChops, ImageEnhance
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
ELA_FOLDER = "static/ELA_Images"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ELA_FOLDER"] = ELA_FOLDER

# ✅ Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ELA_FOLDER, exist_ok=True)

# ✅ Load ML model safely
model = joblib.load("tampering_detector.pkl")
scaler = pickle.load(open("scaler.pkl", "rb"))

# -------------------------
# ELA GENERATION
# -------------------------
def generate_ela(image_path):

    filename = os.path.basename(image_path)
    temp_path = os.path.join(UPLOAD_FOLDER, "temp_" + filename)

    image = Image.open(image_path).convert("RGB")
    image.save(temp_path, "JPEG", quality=90)

    compressed = Image.open(temp_path)

    ela_image = ImageChops.difference(image, compressed)

    extrema = ela_image.getextrema()
    max_diff = max([ex[1] for ex in extrema])

    scale = 255.0 / max_diff if max_diff != 0 else 1

    ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)

    ela_filename = "ela_" + filename
    ela_path = os.path.join(app.config["ELA_FOLDER"], ela_filename)

    ela_image.save(ela_path)

    return ela_path


# -------------------------
# TAMPER REGION DETECTION
# -------------------------
def highlight_tampering(ela_path):

    img = cv2.imread(ela_path)

    if img is None:
        return ela_path  # fallback

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        if cv2.contourArea(cnt) > 300:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(img, (x, y), (x+w, y+h), (0,0,255), 2)

    result_path = ela_path.replace("ela_", "tamper_")

    cv2.imwrite(result_path, img)

    return result_path


# -------------------------
# FEATURE EXTRACTION
# -------------------------
def extract_features(image_path):

    img = cv2.imread(image_path)

    if img is None:
        return np.zeros((1,36))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    focal_length = iso = exposure_time = aperture = orientation = 0

    try:
        exif_dict = piexif.load(image_path)

        focal_length = exif_dict["Exif"].get(piexif.ExifIFD.FocalLength, (0,0))[0]
        iso = exif_dict["Exif"].get(piexif.ExifIFD.ISOSpeedRatings, 0)
        exposure_time = exif_dict["Exif"].get(piexif.ExifIFD.ExposureTime, (0,0))[0]
        aperture = exif_dict["Exif"].get(piexif.ExifIFD.FNumber, (0,0))[0]
        orientation = exif_dict["0th"].get(piexif.ImageIFD.Orientation, 0)

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
            patches.append(np.mean(gray[i:i+32, j:j+32]))

    patch_mean = np.mean(patches) if patches else 0

    features = np.array([
        focal_length, iso, exposure_time, aperture, orientation,
        dct_mean, noise_mean, patch_mean, dct_std, noise_std
    ])

    features = np.pad(features, (0, 36 - len(features)), 'constant')

    return features.reshape(1, -1)


# -------------------------
# HOME PAGE
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -------------------------
# PREDICT
# -------------------------
@app.route("/predict", methods=["POST"])
def predict():

    if "image" not in request.files:
        return "No file uploaded"

    file = request.files["image"]

    if file.filename == "":
        return "No selected file"

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    file.save(filepath)

    # ✅ Generate ELA
    ela_path = generate_ela(filepath)

    # ✅ Extract features
    features = extract_features(filepath)
    features = scaler.transform(features)

    prediction = model.predict(features)[0]

    result = "Tampered Image" if prediction == 1 else "Authentic Image"

    # ✅ Highlight tampering
    if prediction == 1:
        tamper_path = highlight_tampering(ela_path)
    else:
        tamper_path = ela_path

    return render_template(
        "result.html",
        prediction=result,
        img_path=filepath,
        ela_path=ela_path,
        tamper_path=tamper_path
    )


if __name__ == "__main__":
    app.run(debug=True)