# Challenger Task — 헬스케어 데이터 기반 AI 디지털 의료 웹 서비스 개발자 양성과정 [6기]

오즈코딩스쿨 챌린지 과제 모음. 폴더명은 `챌린지번호_주요내용` 규칙으로 정리했다.

## 웹 파트 (HTML/CSS · Javascript)

| 챌린지 | 강의 | 주제 | 폴더 |
| --- | --- | --- | --- |
| 52 | HTML/CSS 1일차 | 내 이력서 만들기 (단일 파일) | `52_HTML기초_내이력서만들기` |
| 53 | HTML/CSS 2일차 | 이력서 전송 폼 추가 | `53_HTML폼_이력서전송폼추가` |
| 54 | HTML/CSS 3일차 | 외부 CSS 분리 · 반응형 · 인쇄 | `54_CSS스타일링_이력서디자인완성` |
| 55 | Javascript 1일차 | 콘솔 사칙연산 계산기 | `55_JS기초_콘솔사칙연산계산기` |
| 56 | Javascript 2일차 | 버튼 계산기 (DOM · 이벤트) | `56_JS_DOM_버튼계산기` |
| 57 | Javascript 3일차 | 암호화폐 가격 추적기 (비동기) | `57_JS비동기_암호화폐가격추적기` |

이력서 3종은 모던 포트폴리오 형식(sticky 내비 · 히어로 프로필 카드 · 타임라인 · 카드 그리드)으로 통일했고,
단계마다 배우는 내용이 드러나게 구성했다.

| | 52 (1일차) | 53 (2일차) | 54 (3일차) |
| --- | --- | --- | --- |
| CSS 위치 | 내부 `<style>` | 내부 `<style>` | **외부 파일 분리** |
| 섹션 | 소개 · 학력 · 경력 · 스킬 · 자격증 · 연락처 | + **프로젝트** · **전송 폼** | + **연구실적 · 수상** |
| 추가 학습 | 시맨틱 구조 · Flexbox/Grid | 폼 요소 전반 | 반응형 · 인쇄 스타일 |

## Docker 파트

| 챌린지 | 강의 | 주제 | 폴더 |
| --- | --- | --- | --- |
| 66 | Docker 1일차 | Docker 기초 · build & run · Compose | `66_Docker기초_빌드와컴포즈` |
| 67 | Docker 2일차 | volume · MySQL · Redis · worker · **동시성 제어** | `67_Docker볼륨_MySQL_Redis_워커연동` |
| 68 | Docker 3일차 | Docker 전반 정리 · **멀티스테이지 빌드** · 모델 서빙 | `68_Docker종합_FastAPI_Redis_모델서빙` |
| 69 | Docker 4일차 | 당뇨 · 고혈압 위험도 예측 서비스 (모델 · API · UI) | `69_당뇨고혈압위험도예측_모델과API` |
| 70 | Docker 5일차 | 같은 서비스의 **배포 완성** (Nginx · CI · 관측성) | `70_당뇨고혈압위험도예측_도커배포완성` |

## 실행 방법

**웹 (52~57)** — 브라우저로 HTML 파일을 열면 된다.

- 52·53·54 : `resume*.html`. 증명사진은 같은 폴더의 `profile.jpg`
- 55 : `calculator.html` → 콘솔에서 `start()`. `runTests()` 로 자동 검증
- 56 : `calculator_v2.html` → 버튼 또는 키보드 입력
- 57 : `crypto_tracker.html` → Binance 공개 API (인터넷 필요, 30초 자동 갱신)

**Docker (66~70)**

```bash
# 66
cd 66_Docker기초_빌드와컴포즈 && docker compose up -d --build

# 67 (동시성 테스트 포함)
cd 67_Docker볼륨_MySQL_Redis_워커연동
cp .env.example .env && docker compose up -d --build
python load_test.py 50

# 68
cd 68_Docker종합_FastAPI_Redis_모델서빙 && docker compose up -d --build

# 69
cd 69_당뇨고혈압위험도예측_모델과API && docker compose up -d --build   # → localhost:8000

# 70 (운영 구성)
cd 70_당뇨고혈압위험도예측_도커배포완성
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build   # → localhost
```

## 검증 기록

| 챌린지 | 검증 내용 |
| --- | --- |
| 52~54 | 브라우저 렌더링 확인. 올드 마크업(`border="1"` 표, `<hr>`) 0건 |
| 55 | `runTests()` 9건 전부 PASS (우선순위 · 0으로 나누기 · 잘못된 연산자) |
| 56 | `3 + 5 × 2 = 13` — 연산자 우선순위 동작 확인 |
| 57 | Binance 실시간 시세 수신 확인 |
| 66~70 | `docker compose config` 전부 통과, Python 전체 컴파일 |
| 68 | 모델 학습 accuracy 0.783, 추론값 임상적 타당성 확인 |
| 69 | 모델 AUC 0.908 / 0.928, 웹 UI 입력→계산→결과 동작 확인 |
| 70 | 단위 테스트 13건 PASS, 운영 구성 api 포트 격리 확인 |

> Docker 이미지 빌드는 Docker Desktop 이 실행 중일 때 수행한다. 구성 파일 검증(`docker compose config`)은 완료.

## 작업 중 잡은 버그

| 위치 | 문제 | 해결 |
| --- | --- | --- |
| 69 `static/style.css` | `.result { display: flex }` 가 `[hidden]` 을 덮어써 결과가 계산 전부터 노출 | `[hidden] { display: none !important }` 추가 |
| 70 `docker-compose.prod.yml` | Compose 가 `ports` 를 병합해서 `ports: []` 로 포트가 닫히지 않음 → 운영에서 api 가 외부 노출 | 베이스에서 `ports` 제거 후 `expose` 만 사용, 개발 오버레이에서만 개방. CI 회귀 검사 추가 |

## 제출 전 확인

- 이력서 연락처 `010-5890-6592`, 이메일 `hanbiho1023@gmail.com` — 3개 파일 공통
- 70번은 `cp .env.example .env` 후 `CORS_ORIGINS` 를 실제 도메인으로 좁혀야 한다
