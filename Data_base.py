import psycopg2
import random
from datetime import date
from natasha import MoneyExtractor, MorphVocab
import re


host = "localhost"
user = "postgres"
password = "12345"
db_name = "allocationofexpenses"

def normalize_slang(text: str) -> str:

    slang_map = {
        "двадцатку": "двадцать рублей",
        "двадцатка": "двадцать рублей",
        "сотку": "сто рублей",
        "сотка": "сто рублей",
        "пятихатку": "пятьсот рублей",
        "пятихатка": "пятьсот рублей",
        "тыщщу": "тысячу рублей",
        "тыщ": "тысячу рублей",
        "двушку": "двести рублей",
        "трёшку": "триста рублей",
        "полтинник": "пятьдесят рублей",
    }
    for slang, normal in slang_map.items():
        text = re.sub(rf'\b{slang}\b', normal, text)
    return text


def split_text_and_amount(text: str):

    morph = MorphVocab()
    extractor = MoneyExtractor(morph)
    text = text.lower().strip()
    text = normalize_slang(text)

    matches = list(extractor(text))
    if not matches:
        return text, None, None

    match = matches[0]
    amount = match.fact.amount
    currency = match.fact.currency or "RUB"

    if hasattr(match, 'span'):
        start, end = match.span
    elif hasattr(match, 'start') and hasattr(match, 'stop'):
        start, end = match.start, match.stop
    else:
        # fallback — ищем вручную через regex
        found = re.search(r'\d+[.,]?\d*\s*руб', text)
        if found:
            start, end = found.span()
        else:
            start, end = len(text), len(text)

    description = text[:start].strip(" ,.")

    # 2.6. Если Natasha не смогла выделить описание, пробуем regex
    if not description:
        desc_match = re.search(r'(.+?)\s+\d+[.,]?\d*\s*руб', text)
        if desc_match:
            description = desc_match.group(1)

    return description, amount, currency

class Postgresql:
    _instance = None

    def __new__(cls, host, user, password, db_name):
        if cls._instance is None:
            cls._instance = super(Postgresql, cls).__new__(cls)
            cls._instance.connection = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=db_name,
            )
            cls._instance.cur = cls._instance.connection.cursor()
        return cls._instance


    def loggin(self,unical_code, login, password): # регистрация пользователя
        #тут написать проверку
        try:
            self.cur.execute('select username from users where username=%s', (login,))
            result = self.cur.fetchall()
        except Exception as e:
            self.connection.rollback()  # обязательно сделать откат
            raise e

        print(result)
        if result != []:
            if isinstance(unical_code, int):
                self.cur.execute('select * from managers')
                amount_manager = self.cur.fetchall()
                self.cur.execute('insert into users (manager_id, telegram_id, username, password) values (%s,%s,%s,%s)',
                                 (random.randint(1, len(amount_manager)), unical_code, str(login), str(password),))
                self.connection.commit()

    def expenses(self, user_id, category, audio_data):
        self.cur.execute('select user_id from users where telegram_id=%s', (user_id,))
        user_id_db = self.cur.fetchone()
        print(category)
        self.cur.execute('select category_id from categories where name=%s', (category,))
        category_db = self.cur.fetchone()
        print(category_db)
        self.cur.execute('select voice_id, recognized_text from voice_message where audio_data=%s', (audio_data,))
        voice_mess = self.cur.fetchall()
        desc, amount, cur = split_text_and_amount(voice_mess[0][1])
        self.cur.execute('insert into expenses (user_id, category_id, voice_id, amount, description) '
                         'values (%s,%s,%s,%s,%s)', (user_id_db, category_db, voice_mess[0][0], amount, desc))
        self.connection.commit()

    def return_expenses(self, user_id):
        self.cur.execute('''
                            SELECT ex.amount, ex.description, ex.created_at, c.name 
                            FROM expenses ex
                            JOIN users u ON ex.user_id = u.user_id
                            LEFT JOIN categories c ON ex.category_id = c.category_id
                            WHERE u.telegram_id = %s
                            ORDER BY ex.created_at asc
                        ''', (user_id,))
        return self.cur.fetchall()


    def voice_recognize(self, recognize_text, audio_data): # здесь будет прописано хранение аудиозаписей
        self.cur.execute('insert into voice_message (recognized_text, audio_data) values (%s,%s)',
                         (recognize_text, audio_data,))
        self.connection.commit()
        # no_name() отправка в агента обработки текста и обратно в бд
    def close(self):
        self.cur.close()
        self.connection.close()

    def reccurent_templates(self, *args): # запись интервала
        #тут написать для одного напоминания
        self.cur.execute('insert into recurrence_templates(name, interval, time) values (%s,%s,%s)',
                         (args[0], args[1], args[2]))
        self.connection.commit()

    def reminder(self, name, text, telegram_id): # запись напоминания
        self.cur.execute('select recurrence_template_id from recurrence_templates '
                         'where name = %s ORDER BY recurrence_template_id DESC LIMIT 1', (name,))
        recurrence_template_id = self.cur.fetchone()
        self.cur.execute('select user_id from users where telegram_id = %s', (telegram_id,))
        user_id = self.cur.fetchone()
        self.cur.execute('insert into reminders (user_id, recurrence_template_id, text) values (%s,%s,%s)',
                         (user_id, recurrence_template_id, text,))
        self.connection.commit()

    def call_reminder(self, user_id): # Выгрузка напоминаний пользователя
        self.cur.execute("select r.text, r.is_habit, r.is_goal, rt.interval, rt.time, r.reminder_id, "
                         "h.frequency, h.start_date, h.active from reminders r "
                         "join users u on r.user_id = u.user_id "
                         "join recurrence_templates rt on r.recurrence_template_id = rt.recurrence_template_id "
                         "left join habits h on r.reminder_id = h.reminder_id and r.is_habit = true "
                         "where u.telegram_id = %s "
                         "ORDER BY r.reminder_id asc", (user_id,))
        return self.cur.fetchall()

    def delete_reminder(self, reminder_id):
        self.cur.execute("delete from reminders where reminder_id = %s", (reminder_id,))
        self.connection.commit()
    def create_habit(self, frequency, reminder_id):
        today = date.today()
        self.cur.execute("insert into habits (reminder_id, frequency, start_date, active) values (%s,%s,%s,%s)",
                         (reminder_id, frequency, today, True))
        self.cur.execute("update reminders set is_habit = True where reminder_id = %s", (reminder_id,))
        self.connection.commit()

db = Postgresql(host, user, password, db_name)
