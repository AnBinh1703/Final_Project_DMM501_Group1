FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir mlflow prometheus_client

COPY deployment/mlflow/exporter.py /app/exporter.py

EXPOSE 5000
EXPOSE 5001
