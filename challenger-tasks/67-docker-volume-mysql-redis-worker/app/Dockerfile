FROM python:3.13-slim

WORKDIR /app

# asyncmy(MySQL 비동기 드라이버)는 사전 빌드 wheel 이 없는 경우 소스 빌드가 필요하다.
# slim 이미지에는 컴파일러가 없어서 gcc 를 설치해야 한다. curl 은 healthcheck 용.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-app.txt requirements-app.txt
RUN pip install --no-cache-dir -r requirements-app.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
