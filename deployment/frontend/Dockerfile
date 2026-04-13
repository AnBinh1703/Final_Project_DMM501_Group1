FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

# Start a simple HTTP server for the frontend
COPY frontend /app/frontend

EXPOSE 8080
WORKDIR /app/frontend
CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0"]
