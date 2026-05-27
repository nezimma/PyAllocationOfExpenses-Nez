# services/speech_service.py — распознавание речи через локальный Whisper
import os
import logging
import threading

# Подавляем предупреждение huggingface о симлинках на Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

logger = logging.getLogger(__name__)

# ─── Конфигурация модели ─────────────────────────────────────────────────────
# Размеры (точность/скорость на CPU):
#   tiny  ~75MB  — очень быстро, плохо слышит акцент
#   base  ~145MB — быстро, приемлемо
#   small ~460MB — хорошо для русского, ~10-20 сек на 30 сек аудио  ← рекомендуется
#   medium ~1.5GB — отлично, но медленно без GPU
_MODEL_NAME = "medium"
_DEVICE = "cpu"
_COMPUTE_TYPE = "int8"  # int8 экономит RAM и ускоряет инференс на CPU

_WHISPER_MODEL = None
_MODEL_LOCK = threading.Lock()


def _get_model():
    """Ленивая загрузка модели — один раз при первом запросе."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        with _MODEL_LOCK:
            if _WHISPER_MODEL is None:
                logger.info(f"Loading Whisper model '{_MODEL_NAME}' (first-time download possible)...")
                from faster_whisper import WhisperModel
                _WHISPER_MODEL = WhisperModel(
                    _MODEL_NAME,
                    device=_DEVICE,
                    compute_type=_COMPUTE_TYPE,
                )
                logger.info("Whisper model ready.")
    return _WHISPER_MODEL


class SpeechRecognitionService:
    """Распознаёт русскую речь через локальный faster-whisper.

    Интерфейс намеренно оставлен совместимым с прежним Google-вариантом.
    wav_path принимается но не используется — Whisper читает ogg/mp3/wav напрямую.
    """

    def convert_and_recognize(self, audio_path: str, wav_path: str | None = None) -> str:
        """Распознаёт аудио и возвращает транскрипт на русском.

        Args:
            audio_path: путь к исходному файлу (.ogg, .wav, .mp3 …)
            wav_path:   игнорируется (оставлен для совместимости с вызывающим кодом)
        """
        return self._recognize(audio_path)

    # ─── Внутренние методы ────────────────────────────────────────────────────

    def _recognize(self, audio_path: str) -> str:
        try:
            model = _get_model()
            segments, _info = model.transcribe(
                audio_path,
                language="ru",
                beam_size=5,
                vad_filter=True,                          # убирает тишину/фоновый шум
                vad_parameters={"min_silence_duration_ms": 500},
                temperature=0.0,                          # детерминированный результат
                initial_prompt="Расходы, покупки, платежи, рублей.",
                condition_on_previous_text=False,         # предотвращает накопление галлюцинаций
            )
            # segments — генератор, обходим один раз
            text = " ".join(seg.text for seg in segments).strip()
            if not text:
                logger.warning("Whisper returned empty transcript.")
                return "Не удалось распознать речь"
            logger.info(f"Whisper: {text!r}")
            return text
        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_path}")
            return "Ошибка сервиса распознавания речи"
        except Exception as e:
            logger.error(f"Whisper error: {e}", exc_info=True)
            return "Ошибка сервиса распознавания речи"
