"""Data science nodes for Smart Campus Digital Twin.

Trains XGBoost models for energy, canteen, and library prediction.
Uses a random train/test split (default 80/20) with sklearn.
"""

import logging

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)


# ─── Generic train/evaluate/predict ───────────────────────────────────────────


def _split_data(
    data: pd.DataFrame, test_size: float, target: str, random_state: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split data into train/test using sklearn's train_test_split."""
    feature_cols = [c for c in data.columns if c != target]
    X = data[feature_cols]
    y = data[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    logger.info(
        "Split: train=%d rows (%.0f%%), test=%d rows (%.0f%%)",
        len(X_train),
        (1 - test_size) * 100,
        len(X_test),
        test_size * 100,
    )
    return X_train, X_test, y_train, y_test


def _train_xgb(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    params: dict,
) -> XGBRegressor:
    """Train an XGBoost regressor."""
    model = XGBRegressor(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        random_state=params["random_state"],
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train)
    return model


def _evaluate(
    model: XGBRegressor,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    label: str,
) -> dict[str, float]:
    """Evaluate model and log metrics."""
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred, squared=False)

    logger.info("=" * 60)
    logger.info("[%s] Model Evaluation", label)
    logger.info("  R2 Score : %.4f", r2)
    logger.info("  MAE      : %.4f", mae)
    logger.info("  RMSE     : %.4f", rmse)
    logger.info("=" * 60)
    return {"r2_score": r2, "mae": mae, "rmse": rmse}


# ─── Energy ────────────────────────────────────────────────────────────────────


def train_energy_model(
    energy_features: pd.DataFrame,
    parameters: dict,
    test_size: float,
) -> tuple[XGBRegressor, pd.DataFrame]:
    """Train + evaluate energy forecast model. Returns (model, test_predictions)."""
    target = parameters["target"]
    X_train, X_test, y_train, y_test = _split_data(energy_features, test_size, target)

    model = _train_xgb(X_train, y_train, parameters)
    metrics = _evaluate(model, X_test, y_test, "Energy Forecast")

    # Build test predictions dataframe
    y_pred = model.predict(X_test)
    preds_df = X_test.copy()
    preds_df["actual"] = y_test.values
    preds_df["predicted"] = y_pred
    preds_df["error"] = preds_df["predicted"] - preds_df["actual"]

    logger.info("Energy model trained. Metrics: %s", metrics)
    return model, preds_df


# ─── Canteen ───────────────────────────────────────────────────────────────────


def train_canteen_model(
    canteen_features: pd.DataFrame,
    parameters: dict,
    test_size: float,
) -> tuple[XGBRegressor, pd.DataFrame]:
    """Train + evaluate canteen congestion model."""
    target = parameters["target"]
    X_train, X_test, y_train, y_test = _split_data(canteen_features, test_size, target)

    model = _train_xgb(X_train, y_train, parameters)
    metrics = _evaluate(model, X_test, y_test, "Canteen Congestion")

    y_pred = model.predict(X_test)
    preds_df = X_test.copy()
    preds_df["actual"] = y_test.values
    preds_df["predicted"] = y_pred
    preds_df["error"] = preds_df["predicted"] - preds_df["actual"]

    logger.info("Canteen model trained. Metrics: %s", metrics)
    return model, preds_df


# ─── Library ───────────────────────────────────────────────────────────────────


def train_library_model(
    library_features: pd.DataFrame,
    parameters: dict,
    test_size: float,
) -> tuple[XGBRegressor, pd.DataFrame]:
    """Train + evaluate library congestion model."""
    target = parameters["target"]
    X_train, X_test, y_train, y_test = _split_data(library_features, test_size, target)

    model = _train_xgb(X_train, y_train, parameters)
    metrics = _evaluate(model, X_test, y_test, "Library Congestion")

    y_pred = model.predict(X_test)
    preds_df = X_test.copy()
    preds_df["actual"] = y_test.values
    preds_df["predicted"] = y_pred
    preds_df["error"] = preds_df["predicted"] - preds_df["actual"]

    logger.info("Library model trained. Metrics: %s", metrics)
    return model, preds_df
