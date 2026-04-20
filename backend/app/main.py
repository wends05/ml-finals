import tensorflow as tf
import cv2
import numpy as np
import base64
import binascii
import logging
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import mediapipe as mp
from pathlib import Path
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid int for %s=%r. Using default=%s", name, value, default)
        return default


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid float for %s=%r. Using default=%s", name, value, default)
        return default


def get_env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or default

app = FastAPI()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ALLOWED_ORIGINS = get_env_list("CORS_ALLOW_ORIGINS", ["*"])

# Allow Vite to send POST requests with JSON headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This is our global state that the ESP32 constantly reads
kiosk_state = {
    "status": "waiting",
    "name": "Unknown",
    "confidence": 0.0
}

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(MODELS_DIR / "kiosk_face_model_eff.keras")))
DATASET_TRAIN_DIR = BASE_DIR / "dataset" / "train"

FACE_DETECTOR_MODEL_CANDIDATES = (
    "face_detector.task",
    "detector.tflite",
    "blaze_face_short_range.tflite",
    "blaze_face_full_range.tflite",
)

IMAGE_WIDTH = get_env_int("IMAGE_WIDTH", 224)
IMAGE_HEIGHT = get_env_int("IMAGE_HEIGHT", 224)
IMAGE_SIZE = (IMAGE_WIDTH, IMAGE_HEIGHT)
PADDING = get_env_int("FACE_PADDING", 30)
MIN_DETECTION_CONFIDENCE = get_env_float("MIN_DETECTION_CONFIDENCE", 0.7)
PREDICTION_THRESHOLD = get_env_float("PREDICTION_THRESHOLD", 0.50)

model = None
CLASS_NAMES: list[str] = []
face_detector = None
MODEL_INIT_ERROR: str | None = None


def load_class_names() -> list[str]:
    """Loads class names from dataset/train subdirectories in sorted order."""
    if not DATASET_TRAIN_DIR.exists():
        raise FileNotFoundError(f"Train dataset directory not found: {DATASET_TRAIN_DIR}")

    class_names = sorted(
        entry.name
        for entry in DATASET_TRAIN_DIR.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )

    print(class_names)

    if not class_names:
        raise RuntimeError(f"No class folders found in: {DATASET_TRAIN_DIR}")

    return class_names


def resolve_face_detector_model_path() -> Path:
    """Finds the first available face detector model in backend/models."""
    for model_name in FACE_DETECTOR_MODEL_CANDIDATES:
        candidate = MODELS_DIR / model_name
        if candidate.is_file():
            return candidate

    expected = "\n".join(f"  - {MODELS_DIR / name}" for name in FACE_DETECTOR_MODEL_CANDIDATES)
    raise FileNotFoundError(
        "No MediaPipe face detector model found.\n"
        f"Expected one of:\n{expected}"
    )


def create_face_detector() -> vision.FaceDetector:
    model_path = resolve_face_detector_model_path()
    options = vision.FaceDetectorOptions(
        base_options=python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE,
        min_detection_confidence=MIN_DETECTION_CONFIDENCE,
    )
    logger.info("Using face detector model: %s", model_path.name)
    return vision.FaceDetector.create_from_options(options)


def initialize_runtime() -> None:
    global model, CLASS_NAMES, face_detector, MODEL_INIT_ERROR

    if model is not None and face_detector is not None and CLASS_NAMES:
        return

    try:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"Keras model not found: {MODEL_PATH}")

        model = tf.keras.models.load_model(str(MODEL_PATH))
        CLASS_NAMES = load_class_names()
        face_detector = create_face_detector()
        MODEL_INIT_ERROR = None
        logger.info("Model runtime initialized successfully")
    except Exception as exc:  # pragma: no cover - initialization guard for runtime
        MODEL_INIT_ERROR = str(exc)
        logger.exception("Failed to initialize model runtime: %s", exc)


@app.on_event("startup")
async def startup_event() -> None:
    initialize_runtime()

# Define the expected data structure from Vite
class ImageData(BaseModel):
    image: str


def decode_base64_image(data_url: str) -> np.ndarray:
    """Decodes a data URL base64 image into an OpenCV BGR frame."""
    if "," in data_url:
        encoded_data = data_url.split(",", 1)[1]
    else:
        encoded_data = data_url

    try:
        image_bytes = base64.b64decode(encoded_data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 image payload") from exc

    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode image bytes")

    return frame

@app.post("/api/predict")
async def process_frame(data: ImageData):
    """Vite calls this 2-3 times a second with a base64 image."""
    global kiosk_state

    initialize_runtime()

    if MODEL_INIT_ERROR:
        return {
            "error": "Model runtime is not ready",
            "details": MODEL_INIT_ERROR,
        }
    
    try:
        frame = decode_base64_image(data.image)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = face_detector.detect(mp_image)
        
        if results.detections:
            # We only look at the first face detected
            detection = results.detections[0]
            bbox = detection.bounding_box
            ih, iw, _ = frame.shape
            
            x, y, w, h = int(bbox.origin_x), int(bbox.origin_y), int(bbox.width), int(bbox.height)
            
            # Apply the exact same padding you used in Phase 1
            x_pad = max(0, x - PADDING)
            y_pad = max(0, y - PADDING)
            w_pad = min(iw - x_pad, w + (PADDING * 2))
            h_pad = min(ih - y_pad, h + (PADDING * 2))

            # Crop the face
            face_crop = rgb_frame[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]

            if face_crop.size != 0:
                # 4. Resize to exactly match MobileNetV2 inputs
                face_resized = cv2.resize(face_crop, IMAGE_SIZE)
                
                # Convert to array and expand dimensions from (224,224,3) to (1,224,224,3)
                # Keras models always expect a "batch" of images, even if it's just a batch of 1.
                input_arr = tf.keras.preprocessing.image.img_to_array(face_resized)
                input_arr = np.expand_dims(input_arr, axis=0)

                # 5. Run the actual Deep Learning prediction
                # verbose=0 stops it from spamming your terminal 3 times a second
                predictions = model.predict(input_arr, verbose=0) 
                
                # 6. Interpret the results
                confidence = float(np.max(predictions[0]))
                class_idx = int(np.argmax(predictions[0]))
                if class_idx >= len(CLASS_NAMES):
                    raise RuntimeError(
                        f"Predicted class index {class_idx} out of range for {len(CLASS_NAMES)} class names"
                    )
                predicted_name = CLASS_NAMES[class_idx]

                print(f"Predicted: {predicted_name} with confidence {confidence:.2f}")

                # 7. Apply a confidence threshold (Trial and Error step!)
                # If the AI is less than 85% sure, it rejects the person.
                if confidence >= PREDICTION_THRESHOLD and predicted_name != "unknown":
                    kiosk_state["status"] = "recognized"
                    kiosk_state["name"] = predicted_name.replace("_", " ").title() # Cleans "student_a" to "Student A"
                else:
                    kiosk_state["status"] = "waiting"
                    kiosk_state["name"] = "Unknown"
                
                kiosk_state["confidence"] = confidence

        else:
            # If MediaPipe doesn't see a face at all
            kiosk_state["status"] = "waiting"
            kiosk_state["name"] = "No face detected"
            kiosk_state["confidence"] = 0.0
            
        return kiosk_state
        
    except Exception as e:
        logger.exception("Error processing frame: %s", e)
        return {"error": str(e)}

@app.get("/api/kiosk-status")
def get_kiosk_status():
    """ESP32 will instantly get the latest state from here."""
    # on address http://127.0.0.1:3009/api/kiosk-status
    # on esp32: http://<your-computer-ip>:3009/api/kiosk-status
    # test by displaying kiosk_state["status"]
    return kiosk_state


@app.get("/api/health")
def health_check():
    # on esp32: http://<your-computer-ip>:3009/api/health
    return {
        "ok": MODEL_INIT_ERROR is None,
        "model_loaded": model is not None,
        "classes_loaded": len(CLASS_NAMES),
        "detector_loaded": face_detector is not None,
        "error": MODEL_INIT_ERROR,
    }

if __name__ == "__main__":
  
    uvicorn.run(app, host="0.0.0.0", port=3009)
