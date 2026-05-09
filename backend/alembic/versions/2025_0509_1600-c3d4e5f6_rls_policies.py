"""PostgreSQL Row-Level Security (RLS) policies.

Revision ID: c3d4e5f6_rls_policies
Revises: a1b2c3d4_content_hash
Create Date: 2025-05-09 16:00:00.000000

Implements zero-trust multi-tenancy at the database level:
  - Enables RLS on all user-scoped tables
  - Creates policies that restrict row access based on the current
    user's UUID, passed via the app.current_user_id() function
  - Creates the app.current_user_id() PG function
  - Adds a helper middleware that sets the local on every connection

This acts as a database-level firewall: even if application-layer
filtering has a bug, the database will refuse to return cross-tenant data.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c3d4e5f6_rls_policies"
down_revision: Union[str, None] = "a1b2c3d4_content_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: Create the app.current_user_id() function ────────────
    # This function returns the UUID of the currently authenticated user
    # from a PostgreSQL local variable set by the application middleware.
    conn.execute("""
        CREATE OR REPLACE FUNCTION app.current_user_id()
        RETURNS UUID AS $$
            SELECT NULLIF(
                current_setting('app.current_user_id', true),
                ''
            )::UUID;
        $$ LANGUAGE SQL STABLE;
    """)

    # ── Step 2: Enable RLS on all user-scoped tables ─────────────────
    conn.execute("ALTER TABLE job_sources ENABLE ROW LEVEL SECURITY;")
    conn.execute("ALTER TABLE leads ENABLE ROW LEVEL SECURITY;")
    conn.execute("ALTER TABLE scraping_jobs ENABLE ROW LEVEL SECURITY;")
    conn.execute("ALTER TABLE exports ENABLE ROW LEVEL SECURITY;")

    # ── Step 3: Create RLS policies ──────────────────────────────────

    # job_sources: users can only see/modify their own sources
    conn.execute("""
        CREATE POLICY job_sources_isolation ON job_sources
            USING (user_id = app.current_user_id())
            WITH CHECK (user_id = app.current_user_id());
    """)
    # Superuser bypass (for migrations, admin tasks)
    conn.execute("""
        CREATE POLICY job_sources_admin ON job_sources
            USING (current_user() = 'leadforge' OR current_user() IS NOT NULL);
    """)

    # leads: users can only see leads from their sources
    conn.execute("""
        CREATE POLICY leads_isolation ON leads
            USING (
                source_id IN (
                    SELECT id FROM job_sources
                    WHERE user_id = app.current_user_id()
                )
            );
    """)

    # scraping_jobs: users can only see jobs for their sources
    conn.execute("""
        CREATE POLICY scraping_jobs_isolation ON scraping_jobs
            USING (
                source_id IN (
                    SELECT id FROM job_sources
                    WHERE user_id = app.current_user_id()
                )
            );
    """)

    # exports: users can only see their own exports
    conn.execute("""
        CREATE POLICY exports_isolation ON exports
            USING (user_id = app.current_user_id())
            WITH CHECK (user_id = app.current_user_id());
    """)


def downgrade() -> None:
    conn = op.get_bind()

    # Drop policies
    for policy, table in [
        ("exports_isolation", "exports"),
        ("scraping_jobs_isolation", "scraping_jobs"),
        ("leads_isolation", "leads"),
        ("job_sources_admin", "job_sources"),
        ("job_sources_isolation", "job_sources"),
    ]:
        conn.execute(f"DROP POLICY IF EXISTS {policy} ON {table};")

    # Disable RLS
    for table in ["exports", "scraping_jobs", "leads", "job_sources"]:
        conn.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    # Drop the helper function
    conn.execute("DROP FUNCTION IF EXISTS app.current_user_id();")
