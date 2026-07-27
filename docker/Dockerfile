# Serving container for the churn classifier (Task 3).
# Build from the repo root so src/ and models/ are in context:
#   docker build -f docker/Dockerfile -t churn-serving:v1 .
FROM python:3.12-slim

WORKDIR /app

# Install serving dependencies first for layer caching.
COPY docker/requirements-serving.txt .
RUN pip install --no-cache-dir -r requirements-serving.txt

# Application code + packaged model (produced by `dvc repro`).
COPY src/ src/
COPY models/model.pkl models/feature_names.json models/

ENV MODEL_PATH=/app/models/model.pkl \
    FEATURE_NAMES_PATH=/app/models/feature_names.json \
    MODEL_VERSION=v1

# Run as non-root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "src.serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
