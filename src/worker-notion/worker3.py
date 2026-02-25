import os
import time
import requests
import mysql.connector
import chromadb
from openai import OpenAI

# 1. 환경 변수 로드
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DB_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
DB_PASSWORD = os.getenv("DB_PASSWORD")

client = OpenAI(api_key=OPENAI_KEY)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_chroma_collection():
    """ChromaDB 컬렉션을 반환합니다."""
    chroma_client = chromadb.HttpClient(host="chromadb-service", port=8000)
    return chroma_client.get_or_create_collection(name="products")

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

def get_embedding(text):
    """OpenAI 임베딩을 생성합니다."""
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

def insert_to_db(product_data):
    """MariaDB에 데이터를 저장하고 id를 반환합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
        INSERT INTO products (name, category, price, description, stock, image_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, product_data)
        conn.commit()
        product_id = cursor.lastrowid
        print(f"✅ MariaDB 저장 성공: {product_data[0]} (id={product_id})")
        return product_id
    except mysql.connector.Error as err:
        print(f"❌ DB 저장 에러: {err}")
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def insert_to_chroma(product_id, name, category, description):
    """ChromaDB에 벡터를 저장합니다."""
    try:
        collection = get_chroma_collection()
        text = f"{name} {category} {description}"
        embedding = get_embedding(text)
        collection.upsert(
            ids=[str(product_id)],
            embeddings=[embedding],
            metadatas=[{"name": name, "category": category, "description": description}],
            documents=[text]
        )
        print(f"✅ ChromaDB 저장 성공: {name}")
    except Exception as e:
        print(f"⚠️ ChromaDB 저장 에러: {e}")

def update_notion_page(page_id, name, category, price, description, stock, image_url):
    """MariaDB 데이터로 노션 페이지를 업데이트합니다."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "category": {
                "select": {"name": category} if category and category != '미분류' else None
            },
            "price": {"number": price},
            "stock": {"number": stock},
            "image_url": {"url": image_url if image_url else None},
            "description": {
                "rich_text": [{"text": {"content": description}}]
            }
        }
    }
    res = requests.patch(url, headers=NOTION_HEADERS, json=data)
    if res.status_code == 200:
        print(f"✅ 노션 업데이트 성공: {name}")
    else:
        print(f"⚠️ 노션 업데이트 실패: {name} - {res.text}")

def get_db_product(name):
    """MariaDB에서 상품 데이터를 가져옵니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE name = %s", (name,))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"❌ DB 조회 에러: {err}")
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def main():
    print("🚀 Worker3 배달원이 노션을 감시 중입니다...")

    while True:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, headers=NOTION_HEADERS)

        if response.status_code == 200:
            pages = response.json().get('results', [])

            for page in pages:
                props = page.get('properties', {})
                page_id = page.get('id')

                try:
                    title_list = props.get('name', {}).get('title', [])
                    if not title_list:
                        continue
                    name = title_list[0].get('plain_text', '')
                    if not name:
                        continue

                    # [Case 1] MariaDB에 이미 있는 상품 → 노션을 MariaDB 기준으로 업데이트
                    if is_already_exists(name):
                        db_product = get_db_product(name)
                        if db_product:
                            update_notion_page(
                                page_id,
                                name,
                                db_product.get('category', '미분류'),
                                db_product.get('price', 0),
                                db_product.get('description', ''),
                                db_product.get('stock', 0),
                                db_product.get('image_url', '')
                            )
                        continue

                    # [Case 2] 새 상품 → GPT description → MariaDB INSERT → ChromaDB 저장 → 노션 업데이트
                    category = (props.get('category', {}).get('select') or {}).get('name', '미분류')
                    price = props.get('price', {}).get('number') or 0
                    stock = props.get('stock', {}).get('number') or 0
                    image_url = props.get('image_url', {}).get('url') or ''

                    print(f"📦 새 상품 발견: '{name}' (GPT 설명 생성 중...)")
                    description = get_gpt_description(name, category)

                    product_data = (name, category, price, description, stock, image_url)
                    product_id = insert_to_db(product_data)

                    if product_id:
                        insert_to_chroma(product_id, name, category, description)

                    update_notion_page(page_id, name, category, price, description, stock, image_url)

                except Exception as e:
                    print(f"⚠️ 데이터 처리 중 오류: {e}")

        time.sleep(30)

if __name__ == "__main__":
    main()