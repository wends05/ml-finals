# Welcome Kiosk - Deep Learning Backend

This backend contains the training workflow, model files, and FastAPI service for the Welcome Kiosk project.

## Prerequisites and Setup

We use `uv` for Python environment management.

```bash
uv sync
```

If you prefer `pip`, install the dependencies from `requirements.txt`.

## Private Data Collection

This project works with private facial data. Keep these rules in mind:

- Do not commit raw image datasets.
- Do not commit generated face samples, misclassification examples, or any artifact that shows a person's face.
- Do not publish filenames or identity labels from private training data unless they have already been anonymized.

The dataset folder is intentionally ignored by git.

## Training Notebooks

The training notebooks live in `backend/scripts/training/`.

- `02_train_dense.ipynb`
- `02_train_model_1.ipynb`
- `02_train_model_2.ipynb`

The most complete privacy-aware analysis notebook is:

- `backend/scripts/training/02_train_model_2.ipynb`

That notebook now includes:

- installation and configuration notes
- data loading and dataset-audit sections
- transfer-learning architecture explanation
- training strategy and callback guidance
- training-curve analysis
- validation metrics and confidence analysis
- optimization recommendations
- export steps for local-only artifacts

## ANALYSIS RESULTS FROM LAST SNAPSHOT

This summary is intentionally privacy-safe. It describes model behavior from the latest saved analysis snapshot without naming any enrolled subject and without embedding face images.

Latest snapshot summary:

- Training images: `480`
- Validation images: `120`
- Enrolled identities: `2`
- Validation accuracy: `0.9917`
- Validation loss: `0.0397`
- Correct validation predictions: `119 / 120`
- Misclassifications: `1`
- Mean confidence on correct predictions: `0.9740`
- Mean confidence on incorrect predictions: `0.7755`
- Best validation epoch from the saved history: `5`

What the model did well:

- It generalized strongly on the held-out validation split.
- It kept validation loss low while maintaining very high validation accuracy.
- It separated the enrolled identities cleanly, with only one saved validation mistake.
- It benefited from a transfer-learning backbone that provides strong visual feature extraction.
- It showed high confidence on most correct predictions, which suggests strong class separation.

Privacy guidance:

- Do not commit notebook-generated artifacts from `backend/scripts/training/artifacts/`.
- Do not publish any sample grids, prediction example images, or raw outputs that may expose a person's face or identifying filenames.
- If charts are needed, run `backend/scripts/training/02_train_model_2.ipynb` locally and generate fresh artifacts on a trusted machine.

Safe outputs to discuss publicly:

- training and validation accuracy curves
- training and validation loss curves
- redacted confusion matrices
- precision, recall, and F1 summaries
- aggregate confidence charts

## Model Training

Run the notebook locally in Jupyter or VS Code.

If you want analysis only, keep the notebook setting:

```python
TRAIN_MODEL = False
```

If you want to retrain the model:

```python
TRAIN_MODEL = True
```

The trained model is saved to:

- `backend/models/kiosk_face_model_eff.keras`

## Backend API

The backend exposes:

- `GET /api/health`
- `POST /api/predict`
- `GET /api/kiosk-status`

You can override the model file with the `MODEL_PATH` environment variable.

## Run the Backend

From the `backend` folder:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

Create a local `.env` from `.env.example`.

Available variables:

- `MODEL_PATH`
- `CORS_ALLOW_ORIGINS`
- `FACE_PADDING`
- `IMAGE_WIDTH`
- `IMAGE_HEIGHT`
- `MIN_DETECTION_CONFIDENCE`
- `PREDICTION_THRESHOLD`

## Deployment Notes

This backend is configured for Vercel with:

- `backend/main.py`
- `backend/vercel.json`
- `backend/requirements.txt`

If model files are missing, the server can still start and expose the health endpoint with an error state.
