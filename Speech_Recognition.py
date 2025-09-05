import os
import speech_recognition as sr
from speech_recognition.recognizers import google, whisper_api


class Speech_voice:
    def convertation(self, audio):
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ru")
            return text
        except sr.UnknownValueError:
            return "Не удалось распознать речь"
        except sr.RequestError:
            return "Ошибка сервиса распознавания речи"



