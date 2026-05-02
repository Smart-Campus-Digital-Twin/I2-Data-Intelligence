"""Initial TimescaleDB schema for I2-Analytics — PDF-Aligned Smart Campus Digital Twin.

This migration sets up:
- Master data tables: 26 buildings, 142 rooms (complete campus topology)
- Academic calendar tables: academic_terms, calendar_events (with venue mapping, fill factors, deterministic seeding)
- Public holidays table: 25 Sri Lanka 2026 holidays with per-room-type occupancy rules
- Time-series hypertable: sensor_readings (1-day chunks, 7-day compression, 90-day retention)
- Alerts table with severity levels
- Materialized views and SQL utility functions
- Campus events: Padura, Food Festival, Symposium, Orientation, Career Fair, Sports, Concerts, Workshops
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Apply initial schema."""
    # Read and execute the full schema.sql
    with open("schema/schema.sql", "r") as f:
        schema_sql = f.read()
    op.execute(sa.text(schema_sql))


def downgrade() -> None:
    """Rollback: drop all I2 schema objects."""
    # Drop in reverse dependency order
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_recent_anomalies CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_latest_occupancy CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS get_occupancy_factor_for_date(DATE) CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS get_current_academic_term() CASCADE;")
    op.execute("DROP TABLE IF EXISTS alerts CASCADE;")
    op.execute("DROP TABLE IF EXISTS sensor_readings CASCADE;")
    op.execute("DROP TABLE IF EXISTS calendar_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS academic_terms CASCADE;")
    op.execute("DROP TABLE IF EXISTS rooms CASCADE;")
    op.execute("DROP TABLE IF EXISTS buildings CASCADE;")
