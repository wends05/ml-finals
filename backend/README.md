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

## Interpretation and Notebook Outputs

Use the following committed notes as your safe, editable interpretation layer:

- `backend/scripts/training/model_2_analysis_report.md`

The report summarizes how the model performed well without naming enrolled identities and without embedding any face images.

Important privacy rule:
- Do not commit notebook-generated artifacts from `backend/scripts/training/artifacts/`.

Those files are ignored on purpose because they may contain:

- private filenames
- identity labels
- face-bearing sample images
- mistake examples from validation data

Instead, whoever runs the notebook should generate those artifacts locally by opening `backend/scripts/training/02_train_model_2.ipynb` and running the cells on their own machine.

Safe outputs to discuss in documentation or presentations:

- training and validation accuracy curves
- training and validation loss curves
- redacted confusion matrices
- precision, recall, and F1 summaries
- aggregate confidence charts
- dataset-balance summaries without identity names

Local-only outputs that should stay private:

- sample face grids
- example prediction images
- raw validation prediction exports with identifying filenames

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
