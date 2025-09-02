import psycopg2


host = "localhost"
user = "postgres"
password = "12345"
db_name = "allocationofexpenses"

try:
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name
    )
    cur = connection.cursor()
    cur.execute("SELECT version();")
    print(f"Version now: {cur.fetchone()}")

except Exception as _ex:
    print("lol")
