import psycopg2


host = "localhost"
user = "postgres"
password = "12345"
db_name = "allocationofexpenses"

class Postgresql:
    def __init__(self, host, user, password, db_name):
        self.connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name,
        )
        self.cur = self.connection.cursor()

    def loggin(self, login, phone_num):
        #тут написать проверку
        self.cur.execute('select login from logginer where login=%s',(login,))
        result = self.cur.fetchall()
        if result == []:
            if isinstance(login, int) and phone_num[0] == "+":
                self.cur.execute('insert into logginer (login, phone) values (%s,%s)', (login, phone_num[1:13]))
                self.connection.commit()
    def close(self):
        self.cur.close()
        self.connection.close()
