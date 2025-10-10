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


    def loggin(self,unical_code, login, password):
        #тут написать проверку
        self.cur.execute('select login from user_tg where login=%s',(login,))
        result = self.cur.fetchall()
        if result == []:
            if isinstance(unical_code, int) and login[0] == "+":
                self.cur.execute('insert into user_tg (unical_code, login, password) values (%s,%s,%s)', (unical_code, login[1:13], password))
                self.connection.commit()
    def close(self):
        self.cur.close()
        self.connection.close()
