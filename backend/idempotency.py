from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import JSON, Column, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError


class IdempotencyStore(Protocol):
    def get(self, workspace_id: str, operation: str, key: str) -> dict[str, Any] | None: ...

    def put(self, workspace_id: str, operation: str, key: str, result: dict[str, Any]) -> None: ...


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._results: dict[tuple[str, str, str], dict[str, Any]] = {}

    def get(self, workspace_id: str, operation: str, key: str) -> dict[str, Any] | None:
        return self._results.get((workspace_id, operation, key))

    def put(self, workspace_id: str, operation: str, key: str, result: dict[str, Any]) -> None:
        self._results[(workspace_id, operation, key)] = dict(result)


idempotency_metadata = MetaData()
idempotency_keys = Table(
    "idempotency_keys_v1",
    idempotency_metadata,
    Column("workspace_id", String(120), primary_key=True),
    Column("operation", String(180), primary_key=True),
    Column("idempotency_key", String(180), primary_key=True),
    Column("result", JSON, nullable=False),
)


class SQLAlchemyIdempotencyStore:
    def __init__(self, database_url: str | Engine) -> None:
        self.engine = database_url if isinstance(database_url, Engine) else create_engine(database_url)
        idempotency_metadata.create_all(self.engine)

    def get(self, workspace_id: str, operation: str, key: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            return connection.execute(
                select(idempotency_keys.c.result).where(
                    idempotency_keys.c.workspace_id == workspace_id,
                    idempotency_keys.c.operation == operation,
                    idempotency_keys.c.idempotency_key == key,
                )
            ).scalar_one_or_none()

    def put(self, workspace_id: str, operation: str, key: str, result: dict[str, Any]) -> None:
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    insert(idempotency_keys).values(
                        workspace_id=workspace_id,
                        operation=operation,
                        idempotency_key=key,
                        result=result,
                    )
                )
        except IntegrityError:
            # A concurrent request won the race; callers return the stored result on retry.
            return
