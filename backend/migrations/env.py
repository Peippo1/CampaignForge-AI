from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.campaigns.repository import metadata as campaign_metadata
from backend.brand_kits import brand_metadata
from backend.identity import identity_metadata
from backend.idempotency import idempotency_metadata
from backend.jobs import job_metadata


config = context.config
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = [campaign_metadata, brand_metadata, identity_metadata, job_metadata, idempotency_metadata]


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
