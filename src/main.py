import os
import time
import logging
from prometheus_client import start_http_server
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader

from syncthing_client import SyncthingClient
from router import EventRouter
from inspector import MetadataInspector
from processor import BeetsProcessor

# Налаштування базового логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("TaggerDaemon")

# 1. Ініціалізація OpenTelemetry Resource
resource = Resource.create({"service.name": "music-tagger"})

# --- Налаштування Tracing ---
trace_provider = TracerProvider(resource=resource)
otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

if otlp_endpoint:
    # Відправляємо трейси по OTLP (наприклад, у Grafana Alloy)
    span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    logger.info(f"OTLP Exporter налаштовано на {otlp_endpoint}")
else:
    # Фолбек для локального тестування (Graceful Degradation)
    span_exporter = ConsoleSpanExporter()
    logger.warning("OTEL_EXPORTER_OTLP_ENDPOINT не задано. Трейси будуть виводитись у stdout.")

trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# --- Налаштування Metrics ---
metric_reader = PrometheusMetricReader()
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Створення Prometheus лічильника
processed_counter = meter.create_counter(
    "processed_files_total",
    description="Загальна кількість оброблених музичних файлів"
)

def main():
    # 2. Запуск Prometheus endpoint (Pull-модель)
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

    # 3. Читання критичної конфігурації (Fail-Fast)
    syncthing_url = os.environ.get("SYNCTHING_URL")
    api_key = os.environ.get("SYNCTHING_API_KEY")
    poll_interval = int(os.environ.get("POLL_INTERVAL_SEC", 5))

    if not syncthing_url or not api_key:
        logger.error("[ERROR]: SYNCTHING_URL або SYNCTHING_API_KEY не задані в оточенні!")
        exit(1)

    # 4. Ініціалізація компонентів пайплайну
    client = SyncthingClient(syncthing_url, api_key)
    router = EventRouter()
    inspector = MetadataInspector()
    processor = BeetsProcessor()

    logger.info("Event loop started. В очікуванні подій від Syncthing...")

    # 5. Головний цикл (Event Loop)
    while True:
        try:
            events = client.get_events()
            
            for event in events:
                target_path = router.process_event(event)
                if not target_path:
                    continue  # Подія відфільтрована (сміття)

                # Створюємо Root Span для кожного валідного файлу
                with tracer.start_as_current_span("process_music_file") as span:
                    span.set_attribute("file.path", target_path)
                    
                    logger.info(f"Знайдено новий файл: {target_path}")
                    
                    # Перевірка ідемпотентності (DRY)
                    meta_state = inspector.inspect(target_path)
                    if meta_state.get('is_processed'):
                        logger.info(f"Файл вже оброблено (ідемпотентність): {target_path}")
                        span.set_attribute("status", "skipped")
                        continue

                    # Запуск обробки через Beets
                    result_status = processor.process_file(target_path, meta_state)
                    
                    # Оновлення метрик та спанів
                    span.set_attribute("status", result_status)
                    processed_counter.add(1, {"status": result_status})
                    
        except Exception as e:
            # Ловимо винятки, щоб Event Loop не впав
            logger.error(f"Неочікувана помилка в головному циклі: {e}", exc_info=True)
            
        time.sleep(poll_interval)

if __name__ == "__main__":
    main()