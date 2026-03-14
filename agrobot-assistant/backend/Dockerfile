FROM python:3.10-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /install

COPY requirements.txt .

# Install app dependencies
RUN pip install --prefix=/install/deps --no-warn-script-location \
    -r requirements.txt

# Install CPU-only PyTorch separately
RUN pip install --prefix=/install/deps --no-warn-script-location \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.2 torchvision==0.17.2

# Strip PyTorch bloat: tests, headers, C++ libs, caffe2, debug symbols
RUN set -e; \
    SITE=/install/deps/lib/python3.10/site-packages; \
    rm -rf \
        $SITE/torch/test \
        $SITE/torch/include \
        $SITE/torch/share \
        $SITE/torch/_C/*.h \
        $SITE/torch/utils/benchmark \
        $SITE/torch/utils/bottleneck \
        $SITE/torch/utils/tensorboard \
        $SITE/torch/distributed \
        $SITE/torch/autograd/profiler* \
        $SITE/torch/onnx \
        $SITE/torch/optim \
        $SITE/torch/testing \
        $SITE/caffe2 \
        $SITE/functorch \
    ; \
    find /install/deps -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
    find /install/deps -name "*.pyc" -delete 2>/dev/null; \
    find /install/deps -name "*.pyi" -delete 2>/dev/null; \
    true

# --- Final stage: clean runtime image ---
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=builder /install/deps /usr/local

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app"]
