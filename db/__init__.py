"""Database utilities for I2-Analytics."""

from .migrations import MigrationRunner, run_migrations_if_needed

__all__ = ['MigrationRunner', 'run_migrations_if_needed']
