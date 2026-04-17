# Welcome Kiosk - Deep Learning Backend

This repository contains the Artificial Intelligence and backend server logic for the Welcome Kiosk project. It handles data collection, model training via Transfer Learning, and serves a FastAPI backend to process live images.

## 🛠 Prerequisites & Setup

We use `uv` for lightning-fast Python package management.

1. Initialize the environment and install dependencies:

```bash
uv init
uv add fastapi uvicorn opencv-python mediapipe tensorflow numpy pydantic
```

## Data Collection

To collect face data for training, follow these steps:

1. Gather a diverse set of images of the target individuals. Ensure good lighting and various angles.
2. Organize the images in a directory structure like this:

```data/
├── person1/
│   ├── img1.jpg
│   ├── img2.jpg
│   └── ...
├── person2/
│   ├── img1.jpg
│   ├── img2.jpg
│   └── ...
└── ...
```

3. Run the face collection script to extract and save facial landmarks:

```bash
uv run python scripts/01_collect_faces.py
```

## Model Training

We use Transfer Learning to train our model on the collected face data.

1. Run the training script:

```bash
uv run python scripts/02_train_model.py
```

2. The trained model will be saved in the `models/` directory.

## Deploy Backend to Vercel

This backend is configured for Vercel Python runtime via:

- `backend/main.py` (ASGI entrypoint)
- `backend/vercel.json` (routing/build config)
- `backend/requirements.txt` (deployment dependencies)

### Notes

- The API exposes:
  - `GET /api/health`
  - `POST /api/predict`
  - `GET /api/kiosk-status`
- The model runtime now initializes lazily. If model files are missing, the server still starts and `/api/health` reports the error.
- You can override the default model path with environment variable `MODEL_PATH`.

### Environment variables

This repository includes `backend/.env.example` and it is safe to commit.

- `.env` is ignored by git.
- `.env.example` is tracked by git as a template.

Create your local environment file:

```bash
cp .env.example .env
```

Available variables:

- `MODEL_PATH`
- `CORS_ALLOW_ORIGINS` (comma-separated)
- `FACE_PADDING`
- `IMAGE_WIDTH`
- `IMAGE_HEIGHT`
- `MIN_DETECTION_CONFIDENCE`
- `PREDICTION_THRESHOLD`

For Vercel, add the same keys in Project Settings → Environment Variables.

### Deploy steps

1. Import this repository in Vercel.
2. Set project root to `backend` if deploying backend as a standalone service.
3. Deploy.
4. Verify with `GET /api/health`.
