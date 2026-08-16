FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /work/frontend

COPY agrobot-assistant/frontend/package*.json ./
RUN npm install

COPY agrobot-assistant/frontend/ ./
ENV REACT_APP_API_URL=/api
RUN npm run build


FROM python:3.10-slim-bookworm AS backend-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /work/backend

RUN pip install --prefix=/install/deps --no-warn-script-location \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    "pydantic[email]==2.5.0" \
    sqlalchemy==2.0.23 \
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
    "Pillow>=10.0.0"

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
