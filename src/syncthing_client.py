import os
import time
import requests
import logging

logger = logging.getLogger(__name__)

class SyncthingClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {'X-API-Key': api_key}
        self.last_id_file = '/tmp/syncthing_last_id.txt'
        self.last_id = self._load_last_id()

    def _load_last_id(self) -> int:
        """Відновлює останній оброблений ID події після рестарту контейнера."""
        if os.path.exists(self.last_id_file):
            try:
                with open(self.last_id_file, 'r') as f:
                    return int(f.read().strip())
            except ValueError:
                logger.warning("Невалідний формат last_id. Починаємо з 0.")
        return 0

    def _save_last_id(self, event_id: int):
        """Зберігає ID події для уникнення повторної обробки."""
        self.last_id = event_id
        with open(self.last_id_file, 'w') as f:
            f.write(str(event_id))

    def get_events(self) -> list:
        """
        Виконує long-polling запит до Syncthing.
        Повертає список подій. Має вбудований Exponential Backoff для обробки збоїв.
        """
        url = f"{self.base_url}/rest/events"
        backoff = 1
        max_backoff = 60

        while True:
            params = {'since': self.last_id, 'limit': 100}
            try:
                # timeout=60 гарантує, що запит не висітиме вічно
                response = requests.get(url, headers=self.headers, params=params, timeout=60)
                response.raise_for_status()
                
                events = response.json()
                if events:
                    # Оновлюємо стан останнім отриманим ID
                    self._save_last_id(events[-1]['id'])
                    return events
                
                # Якщо Syncthing повернув порожній масив (подій не було) - робимо новий цикл
                continue

            except requests.exceptions.RequestException as e:
                logger.error(f"[Network Error] Збій підключення до Syncthing: {e}. Рестарт через {backoff} сек.")
                time.sleep(backoff)
                # Збільшуємо час очікування вдвічі, але не більше max_backoff
                backoff = min(backoff * 2, max_backoff)