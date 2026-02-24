import sqlite3
import os
import requests

# 1. 경로 문제 해결: 스크립트 위치 기준 절대 경로 생성
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, 'products.db')

print(f"📍 참조 중인 DB 경로: {db_path}")

# 2. SQLite 연결 및 데이터 추출
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 테이블 존재 여부 재확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products';")
    if not cursor.fetchone():
        print("❌ 에러: 'products' 테이블을 찾을 수 없습니다. DB 파일을 다시 확인해주세요.")
        exit()


    cursor.execute("SELECT id, name, category, price, description, stock, image_url, created_at FROM products")
    rows = cursor.fetchall()
    print(f"📦 DB에서 {len(rows)}개의 아이템을 읽어왔습니다.")
except sqlite3.OperationalError as e:
    print(f"❌ SQLite 에러: {e}")
    exit()

# 3. 노션 API 설정
NOTION_TOKEN = "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"
DATABASE_ID = "311413d1d494800c87a6fe6a1ee32e76"
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# 4. 데이터 전송 루프
print("🚀 노션으로 데이터 전송을 시작합니다...")
success_count = 0

for row in rows:
    # row[0]:id, [1]:name, [2]:category, [3]:price, [4]:description, [5]:stock, [6]:image_url, [7]:created_at
    data = {
        "parent": { "database_id": DATABASE_ID },
        "properties": {
            # 노션 화면과 똑같이 모두 소문자로 변경했습니다.
            "name": { "title": [{ "text": { "content": str(row[1]) } }] },
            "id": { "number": int(row[0]) },
            "category": { "select": { "name": str(row[2]) if row[2] else "미분류" } },
            "price": { "number": int(row[3]) if row[3] else 0 },
            "description": { "rich_text": [{ "text": { "content": str(row[4]) if row[4] else "" } }] },
            "stock": { "number": int(row[5]) if row[5] else 0 },
            "image_url": { "url": str(row[6]) if row[6] else None },
            "created_at": { "rich_text": [{ "text": { "content": str(row[7]) } }] }
        }
    }
    
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    
    if response.status_code == 200:
        print(f"✅ 전송 성공: {row[1]}") # 상품명을 출력하도록 변경
        success_count += 1
    else:
        print(f"❌ 전송 실패 ({row[1]}): {response.status_code}, {response.text}")

print(f"\n✨ 완료! 총 {success_count}개의 데이터가 노션으로 이관되었습니다.")

if 'conn' in locals():
    conn.close()