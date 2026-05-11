"""add_content_hash_and_hnsw_index

Revision ID: a1b2c3d4_content_hash
Revises: beb72cc_initial
Create Date: 2025-05-09 14:00:00.000000

Adds:
  - content_hash column to leads (SHA-256 dedup hash)
  - HNSW vector index on leads.embedding for fast semantic search
"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op
from sqlalchemy import text

revision: str = "a1b2c3d4_content_hash"
down_revision: Union[str, None] = "beb72cc_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add content_hash column for deduplication ──────────────────────
    op.add_column(
        "leads",
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_leads_content_hash",
        "leads",
        ["content_hash"],
        unique=False,
    )

    # ── Create HNSW index on embedding column ─────────────────────────
    # HNSW (Hierarchical Navigable Small World) is an approximate nearest
    # neighbor index that dramatically improves query speed for high-
    # dimensional vectors.  It trades a small amount of recall accuracy
    # for orders-of-magnitude faster searches compared to exact k-NN.
    #
    # Parameters:
    #   m = 16       — max number of connections per layer (default 16)
    #   ef_construction = 64 — size of dynamic candidate list during build
    op.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_leads_embedding_hnsw "
        "ON leads "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    ))


def downgrade() -> None:
    op.drop_index("ix_leads_embedding_hnsw", table_name="leads", if_exists=True)
    op.drop_index("ix_leads_content_hash", table_name="leads")
    op.drop_column("leads", "content_hash")
