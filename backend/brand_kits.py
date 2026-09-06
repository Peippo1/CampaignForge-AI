from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import JSON, Column, MetaData, String, Table, create_engine, insert, select, update
from sqlalchemy.engine import Engine

from backend.campaigns.workflow import InvalidTransitionError, Role, WorkflowActor


@dataclass(frozen=True)
class BrandKit:
    brand_kit_id: str
    workspace_id: str
    name: str
    voice: str
    audiences: tuple[str, ...] = field(default_factory=tuple)
    product_facts: tuple[str, ...] = field(default_factory=tuple)
    required_phrases: tuple[str, ...] = field(default_factory=tuple)
    banned_terms: tuple[str, ...] = field(default_factory=tuple)
    compliance_rules: tuple[str, ...] = field(default_factory=tuple)


class BrandKitRepository(Protocol):
    def save(self, brand_kit: BrandKit) -> None: ...
    def get(self, brand_kit_id: str) -> BrandKit | None: ...
    def list_for_workspace(self, workspace_id: str) -> list[BrandKit]: ...


class InMemoryBrandKitRepository:
    def __init__(self) -> None:
        self._items: dict[str, BrandKit] = {}

    def save(self, brand_kit: BrandKit) -> None:
        self._items[brand_kit.brand_kit_id] = brand_kit

    def get(self, brand_kit_id: str) -> BrandKit | None:
        return self._items.get(brand_kit_id)

    def list_for_workspace(self, workspace_id: str) -> list[BrandKit]:
        return [item for item in self._items.values() if item.workspace_id == workspace_id]


brand_metadata = MetaData()
brand_kits = Table(
    "brand_kits_v1",
    brand_metadata,
    Column("brand_kit_id", String(36), primary_key=True),
    Column("workspace_id", String(120), nullable=False, index=True),
    Column("name", String(160), nullable=False),
    Column("payload", JSON, nullable=False),
)


class SQLAlchemyBrandKitRepository:
    def __init__(self, database_url: str | Engine) -> None:
        self.engine = database_url if isinstance(database_url, Engine) else create_engine(database_url)
        brand_metadata.create_all(self.engine)

    def save(self, brand_kit: BrandKit) -> None:
        payload = asdict(brand_kit)
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(brand_kits.c.brand_kit_id).where(brand_kits.c.brand_kit_id == brand_kit.brand_kit_id)
            ).first()
            statement = (
                update(brand_kits)
                .where(brand_kits.c.brand_kit_id == brand_kit.brand_kit_id)
                .values(name=brand_kit.name, payload=payload)
                if exists
                else insert(brand_kits).values(
                    brand_kit_id=brand_kit.brand_kit_id,
                    workspace_id=brand_kit.workspace_id,
                    name=brand_kit.name,
                    payload=payload,
                )
            )
            connection.execute(statement)

    def get(self, brand_kit_id: str) -> BrandKit | None:
        with self.engine.connect() as connection:
            payload = connection.execute(
                select(brand_kits.c.payload).where(brand_kits.c.brand_kit_id == brand_kit_id)
            ).scalar_one_or_none()
        return _from_payload(payload) if payload else None

    def list_for_workspace(self, workspace_id: str) -> list[BrandKit]:
        with self.engine.connect() as connection:
            payloads = connection.execute(
                select(brand_kits.c.payload).where(brand_kits.c.workspace_id == workspace_id)
            ).scalars()
            return [_from_payload(payload) for payload in payloads]


class BrandKitService:
    def __init__(self, repository: BrandKitRepository | None = None) -> None:
        self.repository = repository or InMemoryBrandKitRepository()

    def create(self, actor: WorkflowActor, *, name: str, voice: str, **fields: Any) -> BrandKit:
        if actor.role not in {Role.OWNER, Role.EDITOR}:
            raise InvalidTransitionError("Only an owner or editor can create a brand kit.")
        kit = BrandKit(
            brand_kit_id=str(uuid4()),
            workspace_id=actor.workspace_id,
            name=name.strip(),
            voice=voice.strip(),
            **{key: tuple(value) for key, value in fields.items()},
        )
        self.repository.save(kit)
        return kit

    def get(self, actor: WorkflowActor, brand_kit_id: str) -> BrandKit:
        kit = self.repository.get(brand_kit_id)
        if kit is None or kit.workspace_id != actor.workspace_id:
            raise KeyError(brand_kit_id)
        return kit

    def list(self, actor: WorkflowActor) -> list[BrandKit]:
        return self.repository.list_for_workspace(actor.workspace_id)


def _from_payload(payload: dict[str, Any]) -> BrandKit:
    tuple_fields = {
        key: tuple(payload.get(key, []))
        for key in ("audiences", "product_facts", "required_phrases", "banned_terms", "compliance_rules")
    }
    return BrandKit(
        brand_kit_id=payload["brand_kit_id"],
        workspace_id=payload["workspace_id"],
        name=payload["name"],
        voice=payload["voice"],
        **tuple_fields,
    )
