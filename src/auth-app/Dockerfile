# 1. 파이썬 기초 환경
FROM python:3.10-slim-bookworm

# [추가] 얼굴 인식을 위해 필요한 리눅스 시스템 라이브러리 (OpenCV용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. 작업 공간 설정
WORKDIR /app

# 3. 라이브러리 목록 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 현재 폴더의 모든 파일 복사
COPY . .

# 5. 서버 실행 (포트는 8001, 실행 파일은 main.py 기준)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]