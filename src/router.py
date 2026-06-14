import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class EventRouter:
    def __init__(self, base_music_dir: str = "/music", unsorted_dir: str = "/music/_unsorted"):
        self.base_music_dir = Path(base_music_dir)
        self.unsorted_dir = Path(unsorted_dir)

    def process_event(self, event: dict) -> str | None:
        """
        Приймає сирий JSON події. 
        Повертає абсолютний шлях до файлу, якщо подія валідна, або None.
        """
        if event.get('type') != 'ItemFinished':
            return None

        data = event.get('data', {})
        
        # Нас цікавлять ТІЛЬКИ створені/оновлені файли (без видалень та директорій)
        if data.get('action') != 'update' or data.get('type') != 'file':
            return None

        # В ItemFinished шлях до файлу лежить в 'item'
        relative_path = data.get('item', '')
        if not relative_path:
            return None

        # Нормалізація шляху (створення абсолютного)
        abs_path = self.base_music_dir / relative_path

        # -- ФІЛЬТРИ ЗАПОБІЖНИКИ --
        
        # 1. Тимчасові файли Syncthing
        if abs_path.suffix == '.tmp' or '~syncthing~' in abs_path.name:
            logger.debug(f"[Drop] Тимчасовий файл ігнорується: {abs_path}")
            return None

        # 2. Файли конфліктів (split brain)
        if 'sync-conflict' in abs_path.name:
            logger.debug(f"[Drop] Файл конфлікту ігнорується: {abs_path}")
            return None

        # 3. Захист від петель: ігноруємо директорію _unsorted
        # Використовуємо parents для перевірки, чи є unsorted_dir батьківською папкою
        if self.unsorted_dir in abs_path.parents or abs_path.parent == self.unsorted_dir:
            logger.debug(f"[Drop] Файл у карантині ігнорується: {abs_path}")
            return None

        # Якщо всі перевірки пройдені, повертаємо абсолютний шлях як рядок
        return str(abs_path)