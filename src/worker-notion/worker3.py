import os
import time
import requests
import mysql.connector
from openai import OpenAI

# 1. 환경 변수 로드 (Kubernetes Secret을 통해 주입)
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DB_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
DB_PASSWORD = os.getenv("DB_PASSWORD")

client = OpenAI(api_key=OPENAI_KEY)

def get_db_connection():
    """MariaDB 연결 객체를 반환합니다."""
    return mysql.connector.connect(
        host="mariadb-service",
        user="root",
        password=DB_PASSWORD,
        database="shop"
    )

def is_already_exists(name):
    """DB에 동일한 이름의 상품이 있는지 확인합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 이름(name)을 기준으로 중복 확인
        cursor.execute("SELECT id FROM products WHERE name = %s", (name,))
        result = cursor.fetchone()
        return result is not None
    except mysql.connector.Error as err:
        print(f"❌ 중복 확인 중 에러: {err}")
        return False
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def get_gpt_description(name, category):
    """GPT를 이용해 상품 상세 설명을 생성합니다."""
    prompt = f"상품명: {name}, 카테고리: {category}. 이 상품을 홍보하는 짧고 매력적인 문구 한 줄을 써줘."
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ GPT 에러: {e}")
        return "멋진 상품입니다!"

def insert_to_db(product_data):
    """MariaDB에 데이터를 저장합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
        INSERT INTO products (name, category, price, description, stock, image_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, product_data)
        conn.commit()
        print(f"✅ MariaDB 배달 성공: {product_data[0]}")
    except mysql.connector.Error as err:
        print(f"❌ DB 저장 에러: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def main():
    print("🚀 Worker3 배달원이 노션을 감시 중입니다...")
    
    while True:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            pages = response.json().get('results', [])
            
            for page in pages:
                props = page.get('properties', {})
                try:
                    # 노션 컬럼 (소문자 기준)
                    name = props.get('name', {}).get('title', [{}])[0].get('plain_text', '')
                    if not name: continue

                    # [중복 체크] 이미 DB에 있는 상품인지 확인
                    if is_already_exists(name):
                        # print(f"⏭️ '{name}'은(는) 이미 DB에 존재하여 건너뜁니다.")
                        continue
                    
                    category = (props.get('category') or {}).get('select', {}).get('name', '미분류')
                    price = (props.get('price') or {}).get('number', 0)
                    stock = (props.get('stock') or {}).get('number', 0)
                    image_url = (props.get('image_url') or {}).get('url', '')

                    print(f"📦 새 상품 발견: '{name}' (GPT 설명 생성 중...)")
                    description = get_gpt_description(name, category)
                    
                    product_data = (name, category, price, description, stock, image_url)
                    insert_to_db(product_data)
                    
                except Exception as e:
                    print(f"⚠️ 데이터 처리 중 오류: {e}")
        
        # 30초마다 한 번씩 노션 확인
        time.sleep(30)

if __name__ == "__main__":
    main()