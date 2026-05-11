"""PostgreSQL Row-Level Security (RLS) policies.

Revision ID: c3d4e5f6_rls_policies
Revises: a1b2c3d4_content_hash
Create Date: 2025-05-09 16:00:00.000000

Implements zero-trust multi-tenancy at the database level.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "c3d4e5f6_rls_policies"
down_revision: Union[str, None] = "a1b2c3d4_content_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Step 1: Create app schema if not exists
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS app;"))

    # Step 2: Create the app.current_user_id() function
    conn.execute(text(
        "CREATE OR REPLACE FUNCTION app.current_user_id() "
        "RETURNS UUID AS $func$ "
        "SELECT NULLIF(current_setting('app.current_user_id', true), '')::UUID; "
        "$func$ LANGUAGE SQL STABLE;"
    ))

    # Step 3: Enable RLS on all user-scoped tables
    conn.execute(text("ALTER TABLE job_sources ENABLE ROW LEVEL SECURITY;"))
    conn.execute(text("ALTER TABLE leads ENABLE ROW LEVEL SECURITY;"))
    conn.execute(text("ALTER TABLE scraping_jobs ENABLE ROW LEVEL SECURITY;"))
    conn.execute(text("ALTER TABLE exports ENABLE ROW LEVEL SECURITY;"))

    # Step 4: Create RLS policies

    # job_sources
    conn.execute(text(
        "CREATE POLICY job_sources_isolation ON job_sources "
        "USING (user_id = app.current_user_id()) "
        "WITH CHECK (user_id = app.current_user_id());"
    ))
    conn.execute(text(
        "CREATE POLICY job_sources_admin ON job_sources "
        "USING (current_user IS NOT NULL);"
    ))

    # leads
    conn.execute(text(
        "CREATE POLICY leads_isolation ON leads "
        "USING (source_id IN ("
        "  SELECT id FROM job_sources WHERE user_id = app.current_user_id()"
        "));"
    ))

    # scraping_jobs
    conn.execute(text(
        "CREATE POLICY scraping_jobs_isolation ON scraping_jobs "
        "USING (source_id IN ("
        "  SELECT id FROM job_sources WHERE user_id = app.current_user_id()"
        "));"
    ))

    # exports
    conn.execute(text(
        "CREATE POLICY exports_isolation ON exports "
        "USING (user_id = app.current_user_id()) "
        "WITH CHECK (user_id = app.current_user_id());"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    for policy, table in [
        ("exports_isolation", "exports"),
        ("scraping_jobs_isolation", "scraping_jobs"),
        ("leads_isolation", "leads"),
        ("job_sources_admin", "job_sources"),
        ("job_sources_isolation", "job_sources"),
    ]:
        conn.execute(text(f"DROP POLICY IF EXISTS {policy} ON {table};"))

    for table in ["exports", "scraping_jobs", "leads", "job_sources"]:
        conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))

    conn.execute(text("DROP FUNCTION IF EXISTS app.current_user_id();"))
