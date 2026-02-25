from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .database import get_db
import chromadb
import os
from openai import OpenAI

app = FastAPI()

# 정적 파일 및 이미지 경로 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/images", StaticFiles(directory="app/static/images"), name="images")

templates = Jinja2Templates(directory="app/templates")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_KEY)

def get_chroma_collection():
    chroma_client = chromadb.HttpClient(host="chromadb-service", port=8000)
    return chroma_client.get_or_create_collection(name="products")

def get_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

@app.get("/product")
async def index(request: Request, name: str = Query(None), category: str = Query(None)):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if name:
            query += " AND name LIKE %s"
            params.append(f"%{name}%")
        if category:
            query += " AND category LIKE %s"
            params.append(f"%{category}%")
        cursor.execute(query, params)
        products = cursor.fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "products": products})

@app.get("/product/search")
async def rag_search(request: Request, q: str = Query(...)):
    """RAG 기반 의미론적 검색"""
    try:
        # 1. 검색어 임베딩
        embedding = get_embedding(q)

        # 2. ChromaDB에서 유사 상품 검색
        collection = get_chroma_collection()
        results = collection.query(
            query_embeddings=[embedding],
            n_results=5
        )

        # 3. 검색된 상품 id로 MariaDB에서 상세 정보 조회
        product_ids = results['ids'][0]
        products = []
        if product_ids:
            with get_db() as conn:
                cursor = conn.cursor()
                placeholders = ','.join(['%s'] * len(product_ids))
                cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", product_ids)
                products = cursor.fetchall()

        return templates.TemplateResponse("index.html", {
            "request": request,
            "products": products,
            "search_query": q
        })
    except Exception as e:
        print(f"RAG 검색 에러: {e}")
        # ChromaDB 에러 시 일반 검색으로 폴백
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE name LIKE %s OR description LIKE %s",
                         (f"%{q}%", f"%{q}%"))
            products = cursor.fetchall()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "products": products,
            "search_query": q
        })

@app.get("/product/{product_id}")
async def detail(request: Request, product_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    return templates.TemplateResponse("detail.html", {"request": request, "product": product})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)