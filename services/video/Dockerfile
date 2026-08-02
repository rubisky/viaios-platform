# VIAIOS Video Service — Python FastAPI
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn

WORKDIR /app
COPY video_service/main.py .

EXPOSE 8093
HEALTHCHECK --interval=15s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8093/health')" || exit 1

CMD ["python", "main.py"]
