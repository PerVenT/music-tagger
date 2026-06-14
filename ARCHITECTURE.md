```yaml
project_manifest:
  name: "Syncthing Event-Driven Music Tagger"
  architecture_pattern: "Sidecar Daemon, Event-Driven, 12-Factor App"
  
  tech_stack:
    core_sync: "Syncthing (Офіційний образ, без модифікацій)"
    processing_engine: "Beets (Python-фреймворк) + SQLite"
    daemon_language: "Python 3.13+"
    metadata_parser: "mutagen (Python library)"
    observability: "OpenTelemetry SDK (Python) -> Grafana Alloy"

  infrastructure_topology:
    volumes:
      - "/music:/music:rw" # Спільний диск для обох контейнерів
      - "./config:/config:rw" # Директорія для state.db та config.yaml (Beets)
    network: "Гнучка (URL задається через ENV)"
    
  observability_spec:
    metrics: "Pull-модель (Prometheus HTTP Endpoint на порту 8000)"
    traces: "Push-модель (OTLP gRPC/HTTP Exporter)"
    logs: "Stdout (для Docker daemon) + Push в OTLP Exporter"
    business_labels: 
      status: ["sorted", "unsorted"] # Всі статуси вважаються OK (без Error Rate)

  pipeline_logic:
    1_event_listener:
      - "Long-polling Syncthing API (/rest/events)"
      - "Фільтрація: action == 'update', type == 'file'"
    
    2_guardrails_drop_conditions:
      - "Файл має розширення .tmp"
      - "Ім'я містить 'sync-conflict'"
      - "Шлях починається з /music/_unsorted/"
      
    3_idempotency_check:
      - "Скрипт читає аудіо-теги файлу через mutagen"
      - "Якщо присутній тег 'MusicBrainz Track Id' -> Подія ігнорується"
      
    4_beets_execution:
      - "Скрипт викликає 'beet import -q /path/to/file'"
      
    5_routing_and_fallback:
      condition_a_matched:
        description: "Beets успішно розпізнав трек"
        action: "Beets прописує теги, перейменовує файл у '%artist% - %track%' та залишає у поточній директорії (через inline plugin)."
      condition_b_unmatched_with_tags:
        description: "Beets не розпізнав трек, але файл має заповнені теги Artist та Title"
        action: "Python-скрипт перейменовує файл у '%artist% - %track%' і переміщує у корінь /music/_unsorted/."
      condition_c_unmatched_no_tags:
        description: "Beets не розпізнав трек, тегів немає"
        action: "Python-скрипт переміщує файл як є у корінь /music/_unsorted/."

  configuration_management:
    - "Секрети та параметри (SYNCTHING_API_KEY, URL, OTLP_ENDPOINT) передаються виключно через ENV."
    - "Запобіжник: docker-entrypoint.sh генерує базовий beets config.yaml, якщо він відсутній на змонтованому Volume."
```