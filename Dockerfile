FROM python:3.13-slim

# Встановлюємо системні залежності для аудіо-декодування (потрібно для плагіна chroma)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libchromaprint-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Фіксуємо залежності Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    beets \
    mutagen \
    requests \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp \
    prometheus_client

# Створюємо структуру папок для шаблонів та конфігів
RUN mkdir -p /app/templates /config

# Копіюємо вихідний код та скрипти
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
COPY templates/beets_default.yaml /app/templates/beets_default.yaml
COPY src/ /app/src/

RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "src/main.py"]