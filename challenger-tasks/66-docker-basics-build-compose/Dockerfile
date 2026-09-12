# ── 챌린저 66: 가장 기본적인 형태의 Dockerfile ──
# FROM : 베이스 이미지. slim 은 데비안 최소 구성으로 용량이 작다.
FROM python:3.13-slim

# WORKDIR : 이후 명령이 실행될 컨테이너 내부 작업 디렉터리. 없으면 만들어준다.
WORKDIR /app

# 의존성 파일을 먼저 복사한다.
# 소스보다 먼저 복사해야 소스만 바뀔 때 pip install 레이어 캐시가 살아남는다.
COPY requirements.txt requirements.txt

# RUN : 이미지를 "빌드하는 시점"에 실행. --no-cache-dir 로 이미지 용량을 줄인다.
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY main.py main.py

# EXPOSE : 이 컨테이너가 쓰는 포트를 문서화한다. (실제 개방은 -p / ports 가 함)
EXPOSE 8000

# CMD : 컨테이너가 "실행되는 시점"에 도는 기본 명령.
# 0.0.0.0 으로 바인딩해야 컨테이너 외부에서 접속할 수 있다. (127.0.0.1 이면 안 됨)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
