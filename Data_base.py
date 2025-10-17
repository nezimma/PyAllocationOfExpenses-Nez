import psycopg2
import random


host = "localhost"
user = "postgres"
password = "12345"
db_name = "allocationofexpenses"



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


    def loggin(self,unical_code, login, password):
        #тут написать проверку
        self.cur.execute('select username from users where username=%s',(login,))
        result = self.cur.fetchall()
        if result == []:
            if isinstance(unical_code, int):
                self.cur.execute('select * from managers')
                amount_manager = self.cur.fetchall()
                self.cur.execute('insert into users (manager_id, telegram_id, username, password) values (%s,%s,%s,%s)',
                                 (random.randint(1, len(amount_manager)), unical_code, str(login), str(password),))
                self.connection.commit()

    def voice_recognize(self, recognize_text, audio_data):
        self.cur.execute('insert into voice_message (recognized_text, audio_data) values (%s,%s)',
                         (recognize_text, audio_data,))
        self.connection.commit()
        # no_name() отправка в агента обработки текста и обратно в бд
    def close(self):
        self.cur.close()
        self.connection.close()

    def reccurent_templates(self, *args):
        #тут написать для одного напоминания
        self.cur.execute('insert into recurrence_templates(name, interval, time) values (%s,%s,%s)',
                         (args[0], args[1], args[2]))
        self.connection.commit()

    def reminder(self, name, text, telegram_id):
        self.cur.execute('select recurrence_template_id from recurrence_templates '
                         'where name = %s ORDER BY id DESC LIMIT 1', (name,))
        recurrence_template_id = self.cur.fetchone()
        self.cur.execute('select user_id from users where telegram_id = %s', (telegram_id,))
        user_id = self.cur.fetchone()
        self.cur.execute('insert into reminders (user_id, recurrence_template_id, text) values (%s,%s,%s)',
                         (user_id, recurrence_template_id, text,))
        self.connection.commit()

    def call_reminder(self, user_id):
        self.cur.execute("select r.text, r.is_habit, r.is_goal, rt.interval, rt.time, r.reminder_id from reminders r "
                         "join users u on r.user_id = u.user_id "
                         "join recurrence_templates rt on r.recurrence_template_id = rt.recurrence_template_id "
                         "where u.telegram_id = %s", (user_id,))
        return self.cur.fetchall()


db = Postgresql(host, user, password, db_name)
