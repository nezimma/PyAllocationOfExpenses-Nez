import os
import speech_recognition as sr
from speech_recognition.recognizers import google, whisper_api
from pydub import AudioSegment
import subprocess

class Speech_voice:
    def convertation(self, audio_path, wav_path):
        try:
            ffmpeg_cmd = [
                'ffmpeg', '-i', audio_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                wav_path
            ]

            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr.decode()}")
                return

            if not os.path.exists(wav_path):
                return
        except subprocess.TimeoutExpired:
            print("❌ Таймаут обработки аудио")



        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ru")
            return text
        except sr.UnknownValueError:
            return "Не удалось распознать речь"
        except sr.RequestError:
            return "Ошибка сервиса распознавания речи"



