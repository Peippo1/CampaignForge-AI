"""Create hosted campaign, identity, and job tables."""

from alembic import op
import sqlalchemy as sa


revision = "0001_hosted_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces_v1",
        sa.Column("workspace_id", sa.String(length=120), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "memberships_v1",
        sa.Column("workspace_id", sa.String(length=120), primary_key=True),
        sa.Column("user_id", sa.String(length=128), primary_key=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "campaigns_v1",
        sa.Column("campaign_id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_campaigns_v1_workspace_id", "campaigns_v1", ["workspace_id"])
    op.create_table(
        "brand_kits_v1",
        sa.Column("brand_kit_id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_brand_kits_v1_workspace_id", "brand_kits_v1", ["workspace_id"])
    op.create_table(
        "jobs_v1",
        sa.Column("job_id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_jobs_v1_workspace_id", "jobs_v1", ["workspace_id"])
    op.create_table(
        "idempotency_keys_v1",
        sa.Column("workspace_id", sa.String(length=120), primary_key=True),
        sa.Column("operation", sa.String(length=180), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=180), primary_key=True),
        sa.Column("result", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys_v1")
    op.drop_index("ix_brand_kits_v1_workspace_id", table_name="brand_kits_v1")
    op.drop_table("brand_kits_v1")
    op.drop_index("ix_jobs_v1_workspace_id", table_name="jobs_v1")
    op.drop_table("jobs_v1")
    op.drop_index("ix_campaigns_v1_workspace_id", table_name="campaigns_v1")
    op.drop_table("campaigns_v1")
    op.drop_table("memberships_v1")
    op.drop_table("workspaces_v1")
