FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[test]"

COPY src/ src/
COPY tests/ tests/

EXPOSE 8092

CMD ["python", "-m", "capability_service.main"]
