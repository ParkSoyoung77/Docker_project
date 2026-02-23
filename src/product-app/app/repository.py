def search_products(db, name: str = None, category: str = None):
    # products 테이블에서 이름과 카테고리로 필터링 [cite: 37, 38]
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
        
    return db.execute(query, params).fetchall()