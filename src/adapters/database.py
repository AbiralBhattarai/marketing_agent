# adapters/output/postgres/database.py

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from src.domain.models.db_model import BrandDataModel

load_dotenv()


class Database:
    def __init__(
        self,
        min_conn: int = 2,
        max_conn: int = 10,
    ):
        self.pool = ThreadedConnectionPool(
            minconn=min_conn,
            maxconn=max_conn,
            host=os.environ["POSTGRES_HOST"],
            port=os.environ["POSTGRES_PORT"],
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=10,
        )

    @contextmanager
    def connection(self):
        conn = self.pool.getconn()
        try:
            yield conn
        except:
            raise "Could not connect to database"
        finally:
            self.pool.putconn(conn)

    def fetch_one(
        self,
        query: str,
        params: tuple | None = None,
    ) -> BrandDataModel | None:
        with self.connection() as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                cursor.execute(query, params)

                row = cursor.fetchone()

                return dict(row) if row else None

    def close(self):
        self.pool.closeall()