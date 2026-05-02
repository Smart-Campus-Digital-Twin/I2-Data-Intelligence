"""Database migration runner for I2-Analytics."""

import os
import time
from typing import Optional
import logging

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Helper to run database migrations with retry logic."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_s: int = 5,
    ):
        """
        Initialize migration runner.

        Args:
            connection_string: psycopg connection string (e.g., "postgresql://user:pass@localhost/db")
            max_retries: Number of retries before giving up
            retry_delay_s: Delay between retries in seconds
        """
        self.connection_string = connection_string or os.environ.get(
            "TIMESCALE_URL",
            "postgresql://ctuser:ctpass@localhost:5432/campustwin"
        )
        self.max_retries = max_retries
        self.retry_delay_s = retry_delay_s

    def connect(self):
        """Establish database connection with retry."""
        if not psycopg:
            raise ImportError("psycopg3 required: pip install psycopg[binary]")

        for attempt in range(1, self.max_retries + 1):
            try:
                conn = psycopg.connect(self.connection_string)
                logger.info(f"Connected to TimescaleDB on attempt {attempt}")
                return conn
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(
                        f"Connection attempt {attempt} failed: {e}. Retrying in {self.retry_delay_s}s..."
                    )
                    time.sleep(self.retry_delay_s)
                else:
                    logger.error(f"Failed to connect after {self.max_retries} attempts")
                    raise

    def apply_schema(self, schema_file: str) -> None:
        """
        Apply schema from SQL file.

        Args:
            schema_file: Path to schema.sql file
        """
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        with open(schema_file, "r") as f:
            schema_sql = f.read()

        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
            logger.info("Schema applied successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error applying schema: {e}")
            raise
        finally:
            conn.close()

    def health_check(self) -> bool:
        """
        Check if database is healthy and reachable.

        Returns:
            True if database is reachable, False otherwise
        """
        try:
            conn = self.connect()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


def run_migrations_if_needed(schema_file: str = "schema/schema.sql") -> bool:
    """
    Run migrations if they haven't been applied.

    Args:
        schema_file: Path to schema.sql file relative to current directory

    Returns:
        True if migrations were applied successfully
    """
    runner = MigrationRunner()

    if not runner.health_check():
        logger.error("Database not reachable")
        return False

    try:
        runner.apply_schema(schema_file)
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    schema_file = sys.argv[1] if len(sys.argv) > 1 else "schema/schema.sql"
    success = run_migrations_if_needed(schema_file)
    sys.exit(0 if success else 1)
