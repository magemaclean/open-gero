FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 libxext6 libsm6 autodock-vina openbabel \
    && rm -rf /var/lib/apt/lists/* || apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 libxext6 libsm6 \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY apps/api/opengero /app/opengero
COPY apps/worker/worker.py /app/worker.py
COPY data /data

ENV DATASETS_DIR=/data/datasets
ENV TARGETS_DIR=/data/targets
ENV STORAGE_DIR=/var/opengero/storage

CMD ["python", "/app/worker.py"]
