
import cv2
import numpy as np
import base64
import uvicorn
import httpx  # 외부 서비스 호출을 위한 라이브러리 추가
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.detector import BioDetector

# 1. FastAPI 앱 초기화
app = FastAPI()

# 2. 정적 파일 설정 (HTML, CSS, JS 제공)
# static 폴더 내의 파일들을 /static 경로로 접근할 수 있게 합니다.
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. 생체 인식 모듈 초기화
detector = BioDetector()

# 4. 데이터 전송 규격 정의
class AuthData(BaseModel):
    image: str  # 브라우저에서 보낸 Base64 이미지 데이터

# 5. [GET] 메인 인증 페이지 제공
@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="static/index.html 파일을 찾을 수 없습니다.")

# 6. [POST] 실시간 얼굴 인증 엔드포인트
@app.post("/authenticate")
async def authenticate(data: AuthData):
    try:
        # 데이터 URL 스킴(data:image/jpeg;base64,...) 제거 후 디코딩
        header, encoded = data.image.split(",", 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return {"status": "error", "message": "이미지 데이터를 읽을 수 없습니다."}

        # MediaPipe를 이용한 얼굴 랜드마크 및 박스 좌표 추출
        result = detector.get_landmarks(frame)
        

        if result:
            return {
                "status": "success",
                # DNS 이름 대신, Ingress에서 설정할 '경로'를 적어줍니다.
                "redirect_url": "/" 
            }     
        # 인식 실패 시
        return {
            "status": "fail", 
            "message": "인식 중... 얼굴을 정면으로 비춰주세요."
        }

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return {"status": "error", "message": "서버 내부 오류가 발생했습니다."}

# 7. 서버 실행 설정
if __name__ == "__main__":
    # 로컬 테스트 및 컨테이너 배포를 위해 8001번 포트 사용
    # product_service(8000)와 겹치지 않도록 설정함
    uvicorn.run(app, host="0.0.0.0", port=8001)