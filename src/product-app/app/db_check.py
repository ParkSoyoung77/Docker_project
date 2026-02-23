import pandas as pd
import sqlite3

# 데이터베이스 연결
db_path = './db/products.db'
conn = sqlite3.connect(db_path)

# 'products' 테이블의 모든 데이터를 판다스 DataFrame으로 읽기
df = pd.DataFrame()
try:
    df = pd.read_sql_query("SELECT * FROM products", conn)
finally:
    # 연결 종료
    conn.close()

# 데이터 확인
print(df.info())
print(df.head())