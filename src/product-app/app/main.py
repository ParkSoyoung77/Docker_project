from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from .database import get_db

app = FastAPI()

# 정적 파일 및 이미지 경로 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/images", StaticFiles(directory="app/static/images"), name="images")

templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def index(request: Request, name: str = Query(None), category: str = Query(None)):
    with get_db() as db:
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if name:
            query += f" AND name LIKE ?"
            params.append(f"%{name}%")
        if category:
            query += f" AND category LIKE ?"
            params.append(f"%{category}%")
        products = db.execute(query, params).fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "products": products})

@app.get("/product/{product_id}")
async def detail(request: Request, product_id: int):
    with get_db() as db:
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    return templates.TemplateResponse("detail.html", {"request": request, "product": product})