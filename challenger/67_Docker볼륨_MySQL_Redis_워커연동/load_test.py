"""
동시성 테스트 스크립트 (호스트에서 실행)

정원 10명인 슬롯에 50명이 동시에 예약을 요청한다.
LOCK_STRATEGY 에 따라 결과가 어떻게 달라지는지 확인한다.

    python load_test.py            # 기본 50건 동시 요청
    python load_test.py 100        # 100건
"""
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "http://localhost:8000"


def post(path: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else b"{}"
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=20) as res:
        return json.loads(res.read())


def main() -> None:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    print("예약 초기화...")
    post("/reset")

    print(f"{total}명 동시 예약 요청...")
    with ThreadPoolExecutor(max_workers=total) as pool:
        results = list(
            pool.map(
                lambda i: post("/reservations", {"slot_id": 1, "patient_name": f"환자{i:03d}"}),
                range(total),
            )
        )

    success = sum(1 for status, _ in results if status == 200)
    rejected = sum(1 for status, _ in results if status == 409)
    errors = total - success - rejected

    slot = get("/slots/1")
    strategy = next((body.get("strategy") for status, body in results if status == 200), "?")

    print()
    print("=" * 52)
    print(f" 전략        : {strategy}")
    print(f" 정원        : {slot['capacity']}")
    print(f" 요청        : {total}")
    print(f" 성공(200)   : {success}")
    print(f" 마감(409)   : {rejected}")
    print(f" 기타 오류   : {errors}")
    print(f" DB reserved : {slot['reserved']}")
    print(f" 초과 예약   : {slot['oversold']}")
    print("=" * 52)

    if slot["oversold"] > 0:
        print(" ❌ 초과 예약 발생 — 동시성 제어가 필요하다.")
    elif success == slot["capacity"]:
        print(" ✅ 정원만큼만 예약됨 — 동시성 제어 성공.")
    else:
        print(" ⚠️  정원을 채우지 못했다. 락 대기 시간(wait)을 확인할 것.")


if __name__ == "__main__":
    main()
