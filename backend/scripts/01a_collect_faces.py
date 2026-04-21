import cv2
import mediapipe as mp
import os
import time
import random  # Added for randomizing the train/val split
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ==========================================
# CONFIGURATION
# ==========================================
IMAGE_SIZE = (224, 224)  # Required size for EfficientNet/MobileNet
TOTAL_IMAGES = 300       # Increased from 100 to 300 for better data variety
TRAIN_RATIO = 0.8        # 80% for training, 20% for validation
DELAY_MS = 50           # Delay between captures to get varied angles
MIN_DETECTION_CONFIDENCE = 0.7

# Supported model filenames
MODEL_CANDIDATE_FILES = (
    "detector.tflite",
    "blaze_face_short_range.tflite",
    "face_detector.task",
    "blaze_face_full_range.tflite"
)

def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_face_detector_model_path():
    """Finds a compatible FaceDetector model in backend/models."""
    models_dir = os.path.join(get_base_dir(), 'models')
    for model_name in MODEL_CANDIDATE_FILES:
        model_path = os.path.join(models_dir, model_name)
        if os.path.isfile(model_path):
            return model_path

    expected_paths = '\n'.join([f"  - {os.path.join(models_dir, name)}" for name in MODEL_CANDIDATE_FILES])
    raise FileNotFoundError(
        "No MediaPipe face detector model found.\n"
        f"Expected one of:\n{expected_paths}\n\n"
        "Download a model and place it in backend/models."
    )

def create_face_detector():
    """Creates a MediaPipe Tasks FaceDetector in IMAGE mode."""
    model_path = get_face_detector_model_path()
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        min_detection_confidence=MIN_DETECTION_CONFIDENCE,
    )
    return vision.FaceDetector.create_from_options(options), model_path

def setup_directories(class_name):
    """Creates the train and val folders for the specific user."""
    base_dir = get_base_dir()
    train_dir = os.path.join(base_dir, 'dataset', 'train', class_name)
    val_base_dir = os.path.join(base_dir, 'dataset', 'value')

    val_dir = os.path.join(val_base_dir, class_name)
    
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)
    
    return train_dir, val_dir

def main():
    print("=== Welcome Kiosk Data Collector ===")
    class_name = input("Enter the name of the person (e.g., student_a, unknown): ").strip().lower()

    try:
        detector, model_path = create_face_detector()
    except FileNotFoundError as error:
        print(f"Error: {error}")
        return
    
    train_dir, val_dir = setup_directories(class_name)
    
    # Calculate exact number of train vs val images
    num_train = int(TOTAL_IMAGES * TRAIN_RATIO)
    num_val = TOTAL_IMAGES - num_train
    
    # --- NEW: Randomization Logic ---
    # Create a list like ['train', 'train', ..., 'val', 'val'] and shuffle it
    destinations = ['train'] * num_train + ['val'] * num_val
    random.shuffle(destinations)
    
    # Start Video Capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print(f"\nStarting capture for '{class_name}'...")
    print(f"Goal: {TOTAL_IMAGES} total images ({num_train} Train, {num_val} Val)")
    print(f"Using model: {os.path.basename(model_path)}")
    print("Remember to move your head slightly, talk, and change expressions!")
    print("Press 'q' to quit early.\n")
    
    time.sleep(2) # Give user 2 seconds to get ready
    
    count = 0
    with detector:
        while count < TOTAL_IMAGES:
            success, frame = cap.read()
            if not success:
                continue

            # MediaPipe expects RGB images, OpenCV gives BGR
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = detector.detect(mp_image)

            if results.detections:
                # We only care about the first face found in the frame
                detection = results.detections[0]
                bbox = detection.bounding_box
                ih, iw, _ = frame.shape

                x = int(bbox.origin_x)
                y = int(bbox.origin_y)
                w = int(bbox.width)
                h = int(bbox.height)

                # Add a small padding around the face so we don't crop too tightly
                padding = 30
                x_pad = max(0, x - padding)
                y_pad = max(0, y - padding)
                w_pad = min(iw - x_pad, w + (padding * 2))
                h_pad = min(ih - y_pad, h + (padding * 2))

                # Crop the face from the original frame
                face_crop = frame[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]

                # Ensure the crop is valid
                if face_crop.size != 0:
                    # Normalize size to 224x224
                    face_resized = cv2.resize(face_crop, IMAGE_SIZE)

                    # --- NEW: Assign destination based on shuffled list ---
                    current_destination = destinations[count]
                    
                    if current_destination == 'train':
                        save_path = os.path.join(train_dir, f"{class_name}_{count}.jpg")
                        folder_name = "TRAIN"
                    else:
                        save_path = os.path.join(val_dir, f"{class_name}_{count}.jpg")
                        folder_name = "VAL"

                    # Save the image
                    cv2.imwrite(save_path, face_resized)
                    count += 1

                    # Draw a rectangle on the live view
                    box_color = (0, 255, 0) if folder_name == "TRAIN" else (255, 165, 0) # Green for train, Orange for val
                    cv2.rectangle(frame, (x_pad, y_pad), (x_pad+w_pad, y_pad+h_pad), box_color, 2)
                    cv2.putText(frame, f"Captured: {count}/{TOTAL_IMAGES} ({folder_name})",
                                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, box_color, 2)

                    # Wait a tiny bit between captures so images aren't identical
                    cv2.waitKey(DELAY_MS)

            # Show the live feed
            cv2.imshow('Data Collection', frame)

            # Press 'q' to manually quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nCapture interrupted by user.")
                break

    print(f"\n✅ Capture complete! Saved {count} randomly split images for '{class_name}'.")
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
