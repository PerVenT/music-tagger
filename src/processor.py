import os
import time
import shutil
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BeetsProcessor:
    def __init__(self, unsorted_dir: str = "/music/_unsorted"):
        self.unsorted_dir = Path(unsorted_dir)
        # Гарантуємо існування директорії карантину
        self.unsorted_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, text: str) -> str:
        """Видаляє заборонені символи з імені файлу (напр. '/', '\\', ':')."""
        keepcharacters = (' ', '.', '_', '-')
        sanitized = "".join(c for c in text if c.isalnum() or c in keepcharacters)
        return sanitized.strip()

    def process_file(self, file_path: str, metadata: dict) -> str:
        """
        Запускає Beets. Виконує Fallback, якщо Beets проігнорував файл.
        Повертає статус: "sorted" або "unsorted".
        """
        target_path_obj = Path(file_path)

        logger.info(f"[Processor] Запуск Beets для: {file_path}")
        
        # 1. Виклик Beets у повністю тихому режимі
        subprocess.run(
            ['beet', 'import', '-q', str(target_path_obj)], 
            capture_output=True, 
            text=True
        )

        # 2. Перевірка результату Beets
        if not target_path_obj.exists():
            # Beets успішно перейменував/перемістив файл
            logger.info(f"[Processor] Успішно розпізнано та відсортовано.")
            return "sorted"

        # 3. Fallback: Beets не розпізнав трек
        logger.info(f"[Processor] Трек не розпізнано. Запуск Fallback логіки.")
        
        artist = metadata.get('artist')
        title = metadata.get('title')

        # Формування нового імені файлу
        if artist and title:
            safe_artist = self._sanitize_filename(artist)
            safe_title = self._sanitize_filename(title)
            new_filename = f"{safe_artist} - {safe_title}{target_path_obj.suffix}"
            logger.debug(f"[Processor] Знайдено часткові теги. Нове ім'я: {new_filename}")
        else:
            new_filename = target_path_obj.name
            logger.debug(f"[Processor] Тегів немає. Зберігаємо оригінальне ім'я: {new_filename}")

        final_target_path = self.unsorted_dir / new_filename

        # Захист від перезапису (якщо файл з таким іменем вже є в _unsorted)
        if final_target_path.exists():
            timestamp = int(time.time())
            final_target_path = self.unsorted_dir / f"{final_target_path.stem}_{timestamp}{final_target_path.suffix}"

        # Переміщення в директорію карантину
        shutil.move(str(target_path_obj), str(final_target_path))
        logger.info(f"[Processor] Файл переміщено до: {final_target_path}")
        
        return "unsorted"