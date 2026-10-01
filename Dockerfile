FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /work/frontend

# Chromium is only used here, by scripts/prerender.js; it never reaches the runtime image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

COPY agrobot-assistant/frontend/package*.json ./
RUN npm install

COPY agrobot-assistant/frontend/ ./
ENV REACT_APP_API_URL=/api
RUN npm run build && CHROME_PATH=/usr/bin/chromium npm run prerender


FROM python:3.10-slim-bookworm AS backend-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /work/backend

RUN pip install --prefix=/install/deps --no-warn-script-location \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    "pydantic[email]==2.5.0" \
    sqlalchemy==2.0.23 \
    alembic==1.13.1 \
    psycopg2-binary==2.9.9 \
    "psycopg[binary]==3.2.1" \
    "python-jose[cryptography]==3.3.0" \
    "passlib[bcrypt]==1.7.4" \
    bcrypt==3.2.2 \
    python-multipart==0.0.6 \
    httpx==0.25.2 \
    python-dotenv==1.0.0 \
    groq==0.4.1 \
    tavily-python \
    "Pillow>=10.0.0" \
    numpy==2.2.6 \
    pandas==2.3.3 \
    scikit-learn==1.7.2 \
    joblib==1.5.3 \
    xgboost-cpu==3.2.0
# numpy/pandas/scikit-learn/joblib/xgboost are pinned to the versions that
# artifacts/xgboost_crop_model.joblib was saved with.

# CPU-only PyTorch for the disease model; the default wheel pulls in CUDA.
RUN pip install --prefix=/install/deps --no-warn-script-location \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    torch==2.10.0+cpu torchvision==0.25.0+cpu

COPY agrobot-assistant/backend/ ./


FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

COPY --from=backend-builder /install/deps /usr/local
COPY --from=backend-builder /work/backend /app/backend
COPY --from=frontend-builder /work/frontend/build /app/frontend/build

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/backend"]
