"""Data preprocessing nodes for Smart Campus Digital Twin."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


# ─── Shared helpers ────────────────────────────────────────────────────────────

def _extract_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour, day-of-week, month, day-of-year from timestamp."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["day_of_year"] = df["timestamp"].dt.dayofyear
    df["year"] = df["timestamp"].dt.year
    df["is_night"] = ((df["hour"] >= 22) | (df["hour"] <= 5)).astype(int)
    df["is_morning_peak"] = ((df["hour"] >= 8) & (df["hour"] <= 12)).astype(int)
    df["is_afternoon_peak"] = ((df["hour"] >= 13) & (df["hour"] <= 17)).astype(int)
    return df


def _encode_categoricals(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Label-encode string columns to integers."""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = df[col].fillna("unknown")
            df[col] = df[col].astype("category").cat.codes
    return df


# ─── Energy preprocessing ─────────────────────────────────────────────────────

def preprocess_energy(energy_raw: pd.DataFrame) -> pd.DataFrame:
    """Preprocess the energy forecast dataset.

    - Extract temporal features from timestamp
    - Encode building_id, building_type, activity_type
    - Fill NaN in active_events
    - Drop timestamp and holiday_name (string columns)
    """
    logger.info("Preprocessing energy dataset: %d rows", len(energy_raw))

    df = _extract_temporal_features(energy_raw)

    # has_active_event flag
    df["has_active_event"] = df["active_events"].notna().astype(int)

    # Encode categoricals
    df = _encode_categoricals(df, ["building_id", "building_type", "activity_type"])

    # Drop non-numeric columns
    df = df.drop(columns=["timestamp", "holiday_name", "active_events"], errors="ignore")

    # Fill any remaining NaNs
    df = df.fillna(0)

    logger.info(
        "Energy features ready: %d rows, %d columns. Target: total_energy_kwh",
        len(df),
        len(df.columns),
    )
    return df


# ─── Canteen preprocessing ────────────────────────────────────────────────────

def preprocess_canteen(canteen_raw: pd.DataFrame) -> pd.DataFrame:
    """Preprocess the canteen congestion dataset.

    Target: avg (average occupancy count per 30-min window)
    """
    logger.info("Preprocessing canteen dataset: %d rows", len(canteen_raw))

    df = _extract_temporal_features(canteen_raw)

    # Extract half-hour slot from timestamp
    df["half_hour"] = df["timestamp"].dt.minute // 30

    # has_active_event flag
    df["has_active_event"] = df["active_events"].notna().astype(int)

    # Encode categoricals
    df = _encode_categoricals(
        df, ["building_id", "room_id", "room_type", "activity_type", "sensor_type"]
    )

    # Drop leakage columns — these are from the same sensor window as the
    # target (avg) and would give the model an unfair shortcut.
    leakage_cols = ["min", "max", "stddev", "sum_avg", "count"]
    df = df.drop(columns=leakage_cols, errors="ignore")

    # Drop non-numeric columns
    df = df.drop(
        columns=["timestamp", "holiday_name", "active_events"],
        errors="ignore",
    )

    df = df.fillna(0)

    logger.info(
        "Canteen features ready: %d rows, %d columns. Target: avg",
        len(df),
        len(df.columns),
    )
    return df


# ─── Library preprocessing ────────────────────────────────────────────────────

def preprocess_library(library_raw: pd.DataFrame) -> pd.DataFrame:
    """Preprocess the library congestion dataset.

    Target: avg (average occupancy count per 30-min window)
    """
    logger.info("Preprocessing library dataset: %d rows", len(library_raw))

    df = _extract_temporal_features(library_raw)

    # Extract half-hour slot from timestamp
    df["half_hour"] = df["timestamp"].dt.minute // 30

    # has_active_event flag
    df["has_active_event"] = df["active_events"].notna().astype(int)

    # Encode categoricals
    df = _encode_categoricals(
        df, ["building_id", "room_id", "room_type", "activity_type", "sensor_type"]
    )

    # Drop leakage columns — these are from the same sensor window as the
    # target (avg) and would give the model an unfair shortcut.
    leakage_cols = ["min", "max", "stddev", "sum_avg", "count"]
    df = df.drop(columns=leakage_cols, errors="ignore")

    # Drop non-numeric columns
    df = df.drop(
        columns=["timestamp", "holiday_name", "active_events"],
        errors="ignore",
    )

    df = df.fillna(0)

    logger.info(
        "Library features ready: %d rows, %d columns. Target: avg",
        len(df),
        len(df.columns),
    )
    return df
