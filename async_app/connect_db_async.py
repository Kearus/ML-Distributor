# Модуль для асинхронного подключения к БД
from contextlib import asynccontextmanager
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

@asynccontextmanager
async def conn_db():
    try:
        dbname = os.getenv('POSTGRES_DATABASE')
        user = os.getenv('POSTGRES_USER')
        host = os.getenv('POSTGRES_HOSTNAME')
        port = os.getenv('POSTGRES_PORT')
        password = os.getenv('POSTGRES_PASSWORD')

        conn = await asyncpg.connect(database=dbname, user=user,
                                password=password, host=host, port=port)
        yield conn
        await conn.close()

    except Exception as ex:
        print(ex)