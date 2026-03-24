# services/speech_service.py — распознавание речи из аудиофайлов
import os
import subprocess
import logging
import speech_recognition as sr

logger = logging.getLogger(__name__)


class SpeechRecognitionService:
    """Конвертирует .ogg → .wav и распознаёт русскую речь через Google Speech API."""

    def convert_and_recognize(self, audio_path: str, wav_path: str) -> str:
        """Конвертирует аудио и возвращает распознанный текст."""
        if not self._convert_to_wav(audio_path, wav_path):
            return "Ошибка конвертации аудио"
        return self._recognize(wav_path)

    def _convert_to_wav(self, audio_path: str, wav_path: str) -> bool:
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y", wav_path,
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr.decode()}")
                return False
            if not os.path.exists(wav_path):
                logger.error("WAV file was not created")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout")
            return False

    def _recognize(self, wav_path: str) -> str:
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data, language="ru")
        except sr.UnknownValueError:
            return "Не удалось распознать речь"
        except sr.RequestError as e:
            logger.error(f"Google Speech API error: {e}")
            return "Ошибка сервиса распознавания речи"
