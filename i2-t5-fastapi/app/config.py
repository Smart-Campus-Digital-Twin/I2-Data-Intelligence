import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ctuser:ctpass@localhost:5432/campustwin"
)
DB_RETRY_COUNT = int(os.getenv("DB_RETRY_COUNT", "5"))
DB_RETRY_DELAY = float(os.getenv("DB_RETRY_DELAY", "1.0"))  # base seconds for exponential backoff
REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET    = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production-min-32-characters-long")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY    = int(os.getenv("JWT_EXPIRY", "28800"))  # 8 hours
