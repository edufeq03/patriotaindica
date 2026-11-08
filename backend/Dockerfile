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

# Copia e instala requirements a partir do contexto atual
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos
COPY . /app/

# Ajuste de estrutura para que o PYTHONPATH encontre backend.app e database
RUN if [ -d "/app/app" ] && [ ! -d "/app/backend/app" ]; then \
        mkdir -p /app/backend && cp -r /app/app /app/backend/ && cp -r /app/entrypoint.sh /app/backend/ 2>/dev/null || true; \
    fi

# Garantir diretorio static para uploads e permissoes de execucao
RUN mkdir -p /app/static/uploads /app/backend/static/uploads && \
    find /app -name "entrypoint.sh" -exec chmod +x {} + && \
    chown -R appuser:appuser /app

ENV PYTHONPATH=/app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["/bin/sh", "-c", "if [ -f /app/backend/entrypoint.sh ]; then /app/backend/entrypoint.sh; elif [ -f /app/entrypoint.sh ]; then /app/entrypoint.sh; else exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000; fi"]
