FROM python:3.10-slim-bookworm

# 작업 디렉토리 설정
WORKDIR /app

# 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 파이썬이 /app을 루트 패키지 경로로 인식하게 강제 설정
ENV PYTHONPATH=/app

# 실행 명령어: 모듈 방식으로 실행
CMD ["python", "-m", "app.main"]