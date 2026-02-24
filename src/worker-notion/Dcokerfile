FROM python:3.9-slim

WORKDIR /app

# 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사 (src/worker-notion의 내용을 컨테이너 /app으로)
COPY worker3.py .

CMD ["python", "-u", "worker3.py"]