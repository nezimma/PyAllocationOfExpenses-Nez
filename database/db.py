# database/db.py — единственное подключение к PostgreSQL (Singleton)
import psycopg2
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PostgresConnection:
    """Singleton-подключение к PostgreSQL."""

    _instance: Optional["PostgresConnection"] = None

    def __new__(cls, host: str, user: str, password: str, db_name: str, port: int = 5432):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect(host, user, password, db_name, port)
        return cls._instance

    def _connect(self, host, user, password, db_name, port):
        self.connection = psycopg2.connect(
            host=host, user=user, password=password,
            database=db_name, port=port
        )
        self.cur = self.connection.cursor()
        logger.info("Database connection established")

    def execute(self, query: str, params=None):
        try:
            self.cur.execute(query, params)
        except Exception as e:
            self.connection.rollback()
            logger.error(f"DB execute error: {e}")
            raise

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

    def commit(self):
        self.connection.commit()

    def close(self):
        self.cur.close()
        self.connection.close()
        PostgresConnection._instance = None
