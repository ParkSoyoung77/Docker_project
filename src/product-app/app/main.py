from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from .database import get_db

app = FastAPI()

# 정적 파일 및 이미지 경로 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/images", StaticFiles(directory="app/static/images"), name="images")

templates = Jinja2Templates(directory="app/templates")

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

@app.get("/product/detail/{product_id}")
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
    # 0.0.0.0으로 열어야 컨테이너 밖(윈도우)에서 접속이 가능합니다!
    uvicorn.run(app, host="0.0.0.0", port=8081)