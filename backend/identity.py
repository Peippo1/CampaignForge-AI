from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.sql import func

from backend.campaigns.workflow import Role, WorkflowActor


class IdentityError(RuntimeError):
    pass


@dataclass(frozen=True)
class Membership:
    workspace_id: str
    user_id: str
    role: Role


class MembershipDirectory(Protocol):
    def resolve(self, user_id: str, workspace_id: str) -> Membership | None: ...


class InMemoryMembershipDirectory:
    def __init__(self, memberships: list[Membership] | None = None) -> None:
        self._memberships = {(item.user_id, item.workspace_id): item for item in memberships or []}

    def resolve(self, user_id: str, workspace_id: str) -> Membership | None:
        return self._memberships.get((user_id, workspace_id))


identity_metadata = MetaData()
workspaces = Table(
    "workspaces_v1",
    identity_metadata,
    Column("workspace_id", String(120), primary_key=True),
    Column("name", String(160), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
memberships = Table(
    "memberships_v1",
    identity_metadata,
    Column("workspace_id", String(120), primary_key=True),
    Column("user_id", String(128), primary_key=True),
    Column("role", String(20), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


class SQLAlchemyMembershipDirectory:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url)
        identity_metadata.create_all(self.engine)

    def create_workspace(self, workspace_id: str, name: str, owner_user_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(insert(workspaces).values(workspace_id=workspace_id, name=name))
            connection.execute(
                insert(memberships).values(
                    workspace_id=workspace_id,
                    user_id=owner_user_id,
                    role=Role.OWNER.value,
                )
            )

    def resolve(self, user_id: str, workspace_id: str) -> Membership | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(memberships.c.role).where(
                    memberships.c.user_id == user_id,
                    memberships.c.workspace_id == workspace_id,
                )
            ).scalar_one_or_none()
        if row is None:
            return None
        return Membership(workspace_id=workspace_id, user_id=user_id, role=Role(row))


class FirebaseIdentityResolver:
    """Verifies Firebase ID tokens, then resolves authorization from workspace membership."""

    def __init__(self, directory: MembershipDirectory, *, project_id: str) -> None:
        self.directory = directory
        self.project_id = project_id

    def resolve(self, token: str, workspace_id: str) -> WorkflowActor:
        try:
            import firebase_admin
            from firebase_admin import auth

            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(options={"projectId": self.project_id})
            claims = auth.verify_id_token(token, check_revoked=True)
        except Exception as exc:
            raise IdentityError("Invalid or expired identity token.") from exc
        membership = self.directory.resolve(str(claims["uid"]), workspace_id)
        if membership is None:
            raise IdentityError("Workspace access denied.")
        return WorkflowActor(
            user_id=membership.user_id,
            workspace_id=membership.workspace_id,
            role=membership.role,
        )
