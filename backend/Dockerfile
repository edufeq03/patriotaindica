FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar usuario e grupo nao-root com privilegios minimos (M8)
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -s /sbin/nologin -d /app -M appuser

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/

# Garantir diretorio static para uploads e ajustar permissoes
RUN mkdir -p /app/backend/static/uploads && \
    chown -R appuser:appuser /app

ENV PYTHONPATH=/app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
