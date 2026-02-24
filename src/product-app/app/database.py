import pymysql  # sqlite3 대신 pymysql 사용
import os
from contextlib import contextmanager

# 환경 변수에서 접속 정보를 가져옵니다 (deploy.sh에서 넣어줄 정보)
DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "shop")

@contextmanager
def get_db():
    # MariaDB에 접속
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor  # sqlite3.Row와 비슷한 역할
    )
    try:
        yield conn
    finally:
        conn.close()