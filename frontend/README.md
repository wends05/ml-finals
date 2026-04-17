# Frontend - Welcome Kiosk

This is the React + Vite frontend for the Welcome Kiosk project.

## Environment variables

This repository includes `frontend/.env.example` and it is safe to commit.

- `.env` files are ignored by git.
- `.env.example` is tracked as a template.

Create your local environment file:

```bash
cp .env.example .env
```

Available variables:

- `VITE_BACKEND_URL` - Base URL of the backend API (without trailing slash)

Example values:

- Local backend: `http://localhost:8000`
- Deployed backend: `https://your-backend-domain.vercel.app`

## Run locally

```bash
npm install
npm run dev
```

The app reads `VITE_BACKEND_URL` and sends camera frames to:

- `POST {VITE_BACKEND_URL}/api/predict`
