FROM python:3.13-slim

WORKDIR /app

# 워커는 redis 만 쓰므로 컴파일러가 필요 없다 -> 이미지가 훨씬 작다.
COPY requirements-worker.txt requirements-worker.txt
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY worker ./worker

CMD ["python", "-m", "worker.main"]
