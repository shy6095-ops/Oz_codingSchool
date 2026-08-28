import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "xray"


async def save_xray_image(file: UploadFile) -> str:
    today = datetime.now(UTC)
    sub_dir = f"{today:%Y/%m/%d}"
    directory = MEDIA_ROOT / sub_dir
    directory.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "").suffix
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = directory / filename

    with destination.open("wb") as out_file:
        while chunk := await file.read(1024 * 1024):
            out_file.write(chunk)

    return f"/media/xray/{sub_dir}/{filename}"


def delete_local_file(image_url: str) -> None:
    file_path = BASE_DIR / image_url.lstrip("/")
    if file_path.exists():
        os.remove(file_path)
