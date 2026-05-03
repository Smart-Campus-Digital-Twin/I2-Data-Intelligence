import asyncio
import logging
import psycopg
from psycopg.rows import dict_row
from app.config import DATABASE_URL, DB_RETRY_COUNT, DB_RETRY_DELAY
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_db():
    for attempt in range(DB_RETRY_COUNT):
        try:
            async with await psycopg.AsyncConnection.connect(
                DATABASE_URL, row_factory=dict_row
            ) as conn:
                yield conn
                return
        except Exception as exc:
            if attempt + 1 >= DB_RETRY_COUNT:
                logger.exception("Database connection failed after %d attempts", DB_RETRY_COUNT)
                raise HTTPException(status_code=503, detail="Database unavailable") from exc

            wait = DB_RETRY_DELAY * (2 ** attempt)
            logger.warning(
                "Database connection attempt %d/%d failed; retrying in %.1fs",
                attempt + 1,
                DB_RETRY_COUNT,
                wait,
            )
            logger.debug("DB connect error", exc_info=exc)
            await asyncio.sleep(wait)