# Home Greeting System with Face Recognition - Deep Learning Backend

This backend contains the training workflow, model files, and FastAPI service for the Home Greeting System project.

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
- `02_train_model_2_wends.ipynb`

### Notebook Comparison

`02_train_dense.ipynb` and `02_train_model_1.ipynb` were early experiments with smaller datasets and simpler architectures. They are not the focus of current development and may be archived in the future.

`02_train_dense.ipynb` uses dense neural networks for landmark-based features, while `02_train_model_1.ipynb` uses MobileNetV2, which is a lightweight convolutional neural network architecture compared to the more powerful EfficientNetV2B0 used in the later notebooks.

We used `02_train_model_2.ipynb` and `02_train_model_2_wends.ipynb` for 

Both `02_train_model_2.ipynb` and `02_train_model_2_wends.ipynb` use the same pipeline (EfficientNetV2B0 transfer learning, data augmentation, training strategy, and analysis sections). They differ in dataset size and model output:

| Notebook                       | Classes | Train Images | Val Images | Model Output                       | `TRAIN_MODEL` |
| ------------------------------ | ------- | ------------ | ---------- | ---------------------------------- | ------------- |
| `02_train_model_2.ipynb`       | 2       | 480          | 120        | `kiosk_face_model_eff.keras`       | `False`       |
| `02_train_model_2_wends.ipynb` | 11      | 2,640        | 660        | `kiosk_face_model_eff_wends.keras` | `True`        |

## ANALYSIS RESULTS FROM LAST SNAPSHOT

This summary is intentionally privacy-safe. It describes model behavior from the latest saved analysis snapshots without naming any enrolled subject and without embedding face images.

### 2-Class Model (`02_train_model_2.ipynb`)

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

### 11-Class Model (`02_train_model_2_wends.ipynb`)

- Training images: `2,640`
- Validation images: `660`
- Enrolled identities: `11`
- Validation accuracy: `0.9909`
- Validation loss: `0.0840`
- Correct validation predictions: `654 / 660`
- Misclassifications: `6`
- Mean confidence on correct predictions: high (most near 1.0)
- Mean confidence on incorrect predictions: low (all ≤ 0.67)

What both models did well:

- They generalized strongly on the held-out validation split.
- They kept validation loss low while maintaining very high validation accuracy.
- They benefited from a transfer-learning backbone that provides strong visual feature extraction.
- Misclassifications occurred at low confidence, making threshold-based rejection feasible.

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

Each notebook targets a specific model file:

| Notebook                       | Model path                                        |
| ------------------------------ | ------------------------------------------------- |
| `02_train_model_2.ipynb`       | `backend/models/kiosk_face_model_eff.keras`       |
| `02_train_model_2_wends.ipynb` | `backend/models/kiosk_face_model_eff_wends.keras` |

If you want analysis only (skip retraining, use existing model), keep:

```python
TRAIN_MODEL = False
```

If you want to retrain the model:

```python
TRAIN_MODEL = True
```

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
