import csv
import os
import math
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_DIR = os.path.join(BASE_DIR, 'dataset', 'train')
VAL_DIR = os.path.join(BASE_DIR, 'dataset', 'value')

# Output files
TRAIN_CSV = os.path.join(BASE_DIR, 'dataset', 'train_landmarks.csv')
VAL_CSV = os.path.join(BASE_DIR, 'dataset', 'val_landmarks.csv')

# Supported image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

# Face Landmarker task bundle expected in backend/models.
FACE_LANDMARKER_MODEL_CANDIDATES = (
    'face_landmarker.task',
    'face_landmarker_v2.task',
)

# Keep the training CSV compatible with the existing pipeline.
EXPECTED_LANDMARK_COUNT = 468


def resolve_face_landmarker_model_path() -> str:
    """Finds a Face Landmarker task bundle in backend/models."""
    models_dir = os.path.join(BASE_DIR, 'models')

    for model_name in FACE_LANDMARKER_MODEL_CANDIDATES:
        candidate = os.path.join(models_dir, model_name)
        if os.path.isfile(candidate):
            return candidate

    expected_paths = '\n'.join(
        f"  - {os.path.join(models_dir, name)}" for name in FACE_LANDMARKER_MODEL_CANDIDATES
    )
    raise FileNotFoundError(
        "No MediaPipe Face Landmarker task bundle found.\n"
        f"Expected one of:\n{expected_paths}\n\n"
        "Download a Face Landmarker .task file and place it in backend/models."
    )


def create_face_landmarker() -> vision.FaceLandmarker:
    """Creates the MediaPipe Face Landmarker in IMAGE mode."""
    model_path = resolve_face_landmarker_model_path()
    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    return vision.FaceLandmarker.create_from_options(options)


def get_master_class_names(train_dir: str) -> list[str]:
    """Reads the train directory once to create a permanent label mapping."""
    if not os.path.isdir(train_dir):
        raise FileNotFoundError(f"Train directory not found: {train_dir}")
    return sorted(
        name for name in os.listdir(train_dir)
        if os.path.isdir(os.path.join(train_dir, name)) and not name.startswith('.')
    )


def process_folder_to_csv(image_dir: str, output_csv: str, face_landmarker: vision.FaceLandmarker, master_classes: list[str]) -> None:
    """Scans folders, runs Face Landmarker, NORMALIZES coordinates, and saves to CSV."""
    if not os.path.isdir(image_dir):
        print(f"⚠️ Directory not found, skipping: {image_dir}")
        return

    with open(output_csv, mode='w', newline='') as f:
        writer = csv.writer(f)

        # Create header
        header = ['label_idx']
        for i in range(EXPECTED_LANDMARK_COUNT):
            header.extend([f'x{i}', f'y{i}', f'z{i}'])
        writer.writerow(header)

        total_processed = 0
        total_skipped = 0

        # Iterate over the directory
        for class_name in os.listdir(image_dir):
            class_path = os.path.join(image_dir, class_name)
            
            # Skip files or folders that aren't in our master list
            if not os.path.isdir(class_path) or class_name not in master_classes:
                continue

            # Get the correct, permanent label integer
            label_idx = master_classes.index(class_name)
            
            print(f"Processing {class_name} as Label {label_idx} in {image_dir}...")

            image_names = sorted(
                file_name for file_name in os.listdir(class_path)
                if os.path.splitext(file_name)[1].lower() in IMAGE_EXTENSIONS
            )

            for img_name in image_names:
                img_path = os.path.join(class_path, img_name)
                image = cv2.imread(img_path)
                if image is None:
                    total_skipped += 1
                    continue

                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
                results = face_landmarker.detect(mp_image)

                # Skip if no face is found or not enough landmarks are generated
                if not results.face_landmarks or len(results.face_landmarks[0]) < EXPECTED_LANDMARK_COUNT:
                    total_skipped += 1
                    continue

                landmarks = results.face_landmarks[0]
                
                # --- NORMALIZATION LOGIC ---
                # 1. Find the center of the face (Using landmark 1, the tip of the nose)
                nose = landmarks[1]
                cx, cy, cz = nose.x, nose.y, nose.z
                
                # 2. Find the "scale" of the face (max distance from the nose to any other point)
                max_dist = max(
                    math.sqrt((p.x - cx)**2 + (p.y - cy)**2 + (p.z - cz)**2) 
                    for p in landmarks[:EXPECTED_LANDMARK_COUNT]
                )
                
                # Prevent division by zero just in case
                if max_dist == 0: 
                    max_dist = 1.0 

                row = [label_idx]
                
                # 3. Normalize all points: Center them at 0,0,0 and scale them
                for point in landmarks[:EXPECTED_LANDMARK_COUNT]:
                    norm_x = (point.x - cx) / max_dist
                    norm_y = (point.y - cy) / max_dist
                    norm_z = (point.z - cz) / max_dist
                    row.extend([norm_x, norm_y, norm_z])

                writer.writerow(row)
                total_processed += 1

        print(f"Finished {output_csv}! Processed: {total_processed}, Skipped: {total_skipped}")


def main() -> None:
    # 1. Lock in the labels based on the Train folder
    master_classes = get_master_class_names(TRAIN_DIR)
    print(f"Master Label Mapping generated for {len(master_classes)} classes.")
    print(f"Mapping: {dict(enumerate(master_classes))}")

    with create_face_landmarker() as face_landmarker:
        print("\n--- Extracting Train Data ---")
        process_folder_to_csv(TRAIN_DIR, TRAIN_CSV, face_landmarker, master_classes)

        print("\n--- Extracting Validation Data ---")
        process_folder_to_csv(VAL_DIR, VAL_CSV, face_landmarker, master_classes)

    print("\n✅ All data geometrically normalized and extracted to CSV!")


if __name__ == "__main__":
    main()
