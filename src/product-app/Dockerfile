FROM python:3.10-slim-bookworm

# 1. 컨테이너 내부 작업 디렉터리 설정
WORKDIR /app

# 2. 필요한 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 전체 파일 복사 (app 폴더 포함)
COPY . .

# 4. 중요: 파이썬이 현재 디렉터리를 패키지 루트로 인식하게 함
ENV PYTHONPATH=/app

# 5. 실행 방식 (FastAPI/Flask 등 프레임워크에 맞춰 선택 가능)
# 현재 'app.main' 모듈을 실행하도록 설정
CMD ["python", "-m", "app.main"]