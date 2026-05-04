"""Reporting nodes for Smart Campus Digital Twin.

Generates feature importance plots and an insights summary table.
"""

import logging

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)


def _plot_feature_importance(
    model: XGBRegressor,
    title: str,
    top_n: int = 15,
) -> plt.Figure:
    """Plot top-N feature importances from an XGBoost model."""
    importances = model.feature_importances_
    feature_names = model.get_booster().feature_names
    if feature_names is None:
        feature_names = [f"f{i}" for i in range(len(importances))]

    idx = np.argsort(importances)[-top_n:]
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(
        [feature_names[i] for i in idx],
        importances[idx],
        color="#4f8ef7",
        edgecolor="#2563eb",
    )
    ax.set_xlabel("Feature Importance (Gain)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.tick_params(axis="y", labelsize=10)
    fig.tight_layout()
    return fig


def create_energy_feature_importance(
    energy_model: XGBRegressor,
) -> plt.Figure:
    """Generate feature importance chart for energy model."""
    logger.info("Generating energy feature importance plot")
    return _plot_feature_importance(
        energy_model, "Energy Forecast — Top Feature Importances"
    )


def create_canteen_feature_importance(
    canteen_model: XGBRegressor,
) -> plt.Figure:
    """Generate feature importance chart for canteen model."""
    logger.info("Generating canteen feature importance plot")
    return _plot_feature_importance(
        canteen_model, "Canteen Congestion — Top Feature Importances"
    )


def create_library_feature_importance(
    library_model: XGBRegressor,
) -> plt.Figure:
    """Generate feature importance chart for library model."""
    logger.info("Generating library feature importance plot")
    return _plot_feature_importance(
        library_model, "Library Congestion — Top Feature Importances"
    )


def create_insights_report(
    energy_test_predictions: pd.DataFrame,
    canteen_test_predictions: pd.DataFrame,
    library_test_predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Compute summary statistics from test predictions for all 3 models.

    Returns a tidy dataframe with per-model insight rows.
    """
    logger.info("Generating insights report from test predictions")

    rows = []

    # ── Energy insights ────────────────────────────────────────
    e = energy_test_predictions
    e_r2 = 1 - (((e["actual"] - e["predicted"]) ** 2).sum() / ((e["actual"] - e["actual"].mean()) ** 2).sum())
    e_mae = (e["actual"] - e["predicted"]).abs().mean()
    rows.append(
        {
            "model": "Energy Forecast",
            "metric": "R² Score",
            "value": round(e_r2, 4),
        }
    )
    rows.append(
        {"model": "Energy Forecast", "metric": "MAE (kWh)", "value": round(e_mae, 4)}
    )
    rows.append(
        {
            "model": "Energy Forecast",
            "metric": "Mean Actual (kWh)",
            "value": round(e["actual"].mean(), 4),
        }
    )
    rows.append(
        {
            "model": "Energy Forecast",
            "metric": "Mean Predicted (kWh)",
            "value": round(e["predicted"].mean(), 4),
        }
    )
    rows.append(
        {
            "model": "Energy Forecast",
            "metric": "Test Set Size",
            "value": len(e),
        }
    )

    # ── Canteen insights ───────────────────────────────────────
    c = canteen_test_predictions
    c_r2 = 1 - (((c["actual"] - c["predicted"]) ** 2).sum() / ((c["actual"] - c["actual"].mean()) ** 2).sum())
    c_mae = (c["actual"] - c["predicted"]).abs().mean()
    rows.append(
        {
            "model": "Canteen Congestion",
            "metric": "R² Score",
            "value": round(c_r2, 4),
        }
    )
    rows.append(
        {
            "model": "Canteen Congestion",
            "metric": "MAE (occupancy)",
            "value": round(c_mae, 4),
        }
    )
    rows.append(
        {
            "model": "Canteen Congestion",
            "metric": "Mean Actual",
            "value": round(c["actual"].mean(), 4),
        }
    )
    rows.append(
        {
            "model": "Canteen Congestion",
            "metric": "Mean Predicted",
            "value": round(c["predicted"].mean(), 4),
        }
    )
    rows.append(
        {
            "model": "Canteen Congestion",
            "metric": "Test Set Size",
            "value": len(c),
        }
    )

    # ── Library insights ───────────────────────────────────────
    li = library_test_predictions
    l_r2 = 1 - (((li["actual"] - li["predicted"]) ** 2).sum() / ((li["actual"] - li["actual"].mean()) ** 2).sum())
    l_mae = (li["actual"] - li["predicted"]).abs().mean()
    rows.append(
        {
            "model": "Library Congestion",
            "metric": "R² Score",
            "value": round(l_r2, 4),
        }
    )
    rows.append(
        {
            "model": "Library Congestion",
            "metric": "MAE (occupancy)",
            "value": round(l_mae, 4),
        }
    )
    rows.append(
        {
            "model": "Library Congestion",
            "metric": "Mean Actual",
            "value": round(li["actual"].mean(), 4),
        }
    )
    rows.append(
        {
            "model": "Library Congestion",
            "metric": "Mean Predicted",
            "value": round(li["predicted"].mean(), 4),
        }
    )
    rows.append(
        {
            "model": "Library Congestion",
            "metric": "Test Set Size",
            "value": len(li),
        }
    )

    report = pd.DataFrame(rows)
    logger.info("Insights report:\n%s", report.to_string(index=False))
    return report
