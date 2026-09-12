"""
챌린저 67 - Docker를 활용한 웹 서비스 배포 2일차

멀티 컨테이너 구성(FastAPI + MySQL + Redis + worker)에서
진료 예약의 동시성 문제를 재현하고 해결한다.

- LOCK_STRATEGY=none        -> 초과 예약 발생 (문제 재현)
- LOCK_STRATEGY=redis-lock  -> Redis 분산 락으로 해결
- LOCK_STRATEGY=db-lock     -> MySQL SELECT ... FOR UPDATE 로 해결
"""
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal, engine, get_session, init_db
from app.models import Reservation, Slot
from app.redis_client import QUEUE_KEY, distributed_lock, redis


@asynccontextmanager
async def lifespan(_: FastAPI):
    """컨테이너 기동 시 테이블 생성 + 시드 데이터 준비."""
    await init_db()
    await seed_slot()
    yield
    await engine.dispose()
    await redis.aclose()


app = FastAPI(
    title="Docker 2일차 - 진료 예약 API",
    description="volume / MySQL / Redis / worker / 동시성 제어 연습",
    version="1.0.0",
    lifespan=lifespan,
)


class ReserveRequest(BaseModel):
    slot_id: int = 1
    patient_name: str


class ReserveResponse(BaseModel):
    reservation_id: int
    slot_id: int
    reserved: int
    capacity: int
    strategy: str


async def seed_slot() -> None:
    """테스트용 예약 슬롯 1건을 만든다. (이미 있으면 정원만 맞춰둔다)"""
    async with SessionLocal() as session:
        slot = await session.get(Slot, 1)
        if slot is None:
            session.add(
                Slot(
                    id=1,
                    doctor="한승수",
                    start_at=datetime.now() + timedelta(days=1),
                    capacity=settings.SLOT_CAPACITY,
                    reserved=0,
                )
            )
        else:
            slot.capacity = settings.SLOT_CAPACITY
        await session.commit()


@app.get("/healthcheck")
async def healthcheck():
    """compose healthcheck 용. DB/Redis 연결까지 확인한다."""
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ok", "strategy": settings.LOCK_STRATEGY}


@app.get("/slots/{slot_id}")
async def get_slot(slot_id: int, session: AsyncSession = Depends(get_session)):
    slot = await session.get(Slot, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="슬롯을 찾을 수 없습니다.")
    return {
        "slot_id": slot.id,
        "doctor": slot.doctor,
        "capacity": slot.capacity,
        "reserved": slot.reserved,
        "remaining": slot.capacity - slot.reserved,
        "oversold": max(0, slot.reserved - slot.capacity),
    }


async def _reserve(session: AsyncSession, slot_id: int, patient_name: str, lock_row: bool):
    """
    예약 1건을 처리한다.

    lock_row=True 면 SELECT ... FOR UPDATE 로 행을 잠근다.
    잠그지 않으면 read -> check -> write 사이에 다른 트랜잭션이 끼어들어
    정원을 초과해서 예약이 들어간다. (lost update)
    """
    stmt = select(Slot).where(Slot.id == slot_id)
    if lock_row:
        stmt = stmt.with_for_update()

    slot = (await session.execute(stmt)).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="슬롯을 찾을 수 없습니다.")

    if slot.reserved >= slot.capacity:
        raise HTTPException(status_code=409, detail="예약이 마감되었습니다.")

    slot.reserved += 1
    reservation = Reservation(slot_id=slot_id, patient_name=patient_name)
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)

    return reservation, slot


@app.post("/reservations", response_model=ReserveResponse)
async def create_reservation(
    payload: ReserveRequest,
    session: AsyncSession = Depends(get_session),
):
    strategy = settings.LOCK_STRATEGY

    if strategy == "redis-lock":
        # 슬롯 단위로 락을 걸어 확인-증가 구간을 한 번에 하나만 통과시킨다.
        async with distributed_lock(f"lock:slot:{payload.slot_id}", ttl=5):
            reservation, slot = await _reserve(session, payload.slot_id, payload.patient_name, False)
    elif strategy == "db-lock":
        # DB 트랜잭션 안에서 행 잠금. 애플리케이션이 여러 대로 늘어도 안전하다.
        reservation, slot = await _reserve(session, payload.slot_id, payload.patient_name, True)
    else:
        # 아무 보호 없음 -> 동시 요청에서 초과 예약이 발생한다.
        reservation, slot = await _reserve(session, payload.slot_id, payload.patient_name, False)

    # 확정 알림은 워커에게 넘긴다. (요청 응답을 붙잡지 않기 위해)
    await redis.rpush(
        QUEUE_KEY,
        json.dumps(
            {
                "reservation_id": reservation.id,
                "slot_id": slot.id,
                "patient_name": reservation.patient_name,
            },
            ensure_ascii=False,
        ),
    )

    return ReserveResponse(
        reservation_id=reservation.id,
        slot_id=slot.id,
        reserved=slot.reserved,
        capacity=slot.capacity,
        strategy=strategy,
    )


@app.post("/reset")
async def reset(session: AsyncSession = Depends(get_session)):
    """동시성 테스트를 반복하기 위해 예약을 전부 비운다."""
    await session.execute(text("DELETE FROM reservations"))
    await session.execute(text("UPDATE slots SET reserved = 0"))
    await session.commit()
    await redis.delete(QUEUE_KEY)
    return {"status": "reset", "capacity": settings.SLOT_CAPACITY}


@app.get("/notifications")
async def notifications():
    """워커가 처리한 결과를 확인한다. (worker 가 로그 리스트에 쌓아둠)"""
    logs = await redis.lrange("reservation:done", 0, -1)
    return {"count": len(logs), "items": [json.loads(x) for x in logs]}
