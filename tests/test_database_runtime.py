import pytest
from sqlalchemy import inspect

from app.core.db.databases import async_engine, initialize_database


@pytest.mark.anyio
async def test_database_initialization_creates_users_table():
    await initialize_database()

    async with async_engine.connect() as connection:
        tables = await connection.run_sync(lambda sync_connection: inspect(sync_connection).get_table_names())

    assert "users" in tables
