import sqlite3
import json
from datetime import datetime

def create_database():
    """JSON 파일에서 상품 데이터를 읽어 DB 생성"""
    
    # JSON 파일 읽기
    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    conn = sqlite3.connect('./db/products.db')
    cursor = conn.cursor()
    
    # 상품 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT,
        stock INTEGER DEFAULT 0,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # JSON 데이터를 DB에 삽입
    for product in products:
        cursor.execute('''
        INSERT INTO products (name, category, price, description, stock, image_url)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            product['name'],
            product['category'],
            product['price'],
            product['description'],
            product['stock'],
            product['image_url']
        ))
    
    conn.commit()
    conn.close()
    print("상품 DB 생성 완료!")
    print(f"   - 총 {len(products)}개 상품 추가됨")


if __name__ == "__main__":
    create_database()