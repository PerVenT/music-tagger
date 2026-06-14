import logging
from mutagen import File

logger = logging.getLogger(__name__)

class MetadataInspector:
    def inspect(self, file_path: str) -> dict:
        """
        Аналізує аудіофайл.
        Повертає словник зі статусом обробки (is_processed) та базовими тегами для fallback.
        """
        result = {
            'is_processed': False,
            'artist': None,
            'title': None
        }

        try:
            # easy=True уніфікує ключі для різних форматів (mp3, flac, m4a)
            audio = File(file_path, easy=True)
            
            if audio is None:
                logger.warning(f"[Inspector] Не вдалося прочитати аудіо-теги (непідтримуваний формат): {file_path}")
                return result

            # Beets завжди записує musicbrainz_trackid при успішному розпізнаванні
            if 'musicbrainz_trackid' in audio:
                result['is_processed'] = True
                return result

            # Якщо файл не оброблений, відразу витягуємо теги для можливого fallback
            # mutagen повертає значення у вигляді списків
            artist_list = audio.get('artist', [])
            title_list = audio.get('title', [])

            if artist_list and artist_list[0]:
                result['artist'] = artist_list[0]
            if title_list and title_list[0]:
                result['title'] = title_list[0]

        except Exception as e:
            logger.error(f"[Inspector] Помилка читання файлу {file_path}: {e}")

        return result