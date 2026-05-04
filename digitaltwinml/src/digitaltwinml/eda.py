"""
Exploratory Data Analysis (EDA) for Smart Campus Digital Twin Datasets.

Generates comprehensive visualizations for energy, canteen, and library datasets.
Outputs are saved to data/08_reporting/eda/

Usage:
    cd digitaltwinml
    python -m digitaltwinml.eda
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")

# ── Config ────────────────────────────────────────────────────────────────────

# Resolve project root (digitaltwinml/) from this script's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "08_reporting", "eda")
DATASETS = {
    "energy": {
        "path": os.path.join(PROJECT_ROOT, "data", "01_raw", "energy_forecast_2024_2025.csv"),
        "target": "total_energy_kwh",
        "title": "Energy Forecast",
    },
    "canteen": {
        "path": os.path.join(PROJECT_ROOT, "data", "01_raw", "canteen_congestion_2024_2025.csv"),
        "target": "avg",
        "title": "Canteen Congestion",
    },
    "library": {
        "path": os.path.join(PROJECT_ROOT, "data", "01_raw", "library_congestion_2024_2025.csv"),
        "target": "avg",
        "title": "Library Congestion",
    },
}

# Seaborn style
sns.set_theme(style="darkgrid", palette="viridis")
plt.rcParams.update({"figure.max_open_warning": 0})


def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["month"] = df["timestamp"].dt.month
    df["month_name"] = df["timestamp"].dt.strftime("%b")
    df["year"] = df["timestamp"].dt.year
    df["date"] = df["timestamp"].dt.date
    return df


# ── Plot functions ────────────────────────────────────────────────────────────


def plot_target_distribution(df, target, title, out_path):
    """Histogram + KDE of the target variable."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    axes[0].hist(df[target], bins=60, color="#4f8ef7", edgecolor="#2563eb", alpha=0.8)
    axes[0].set_xlabel(target, fontsize=11)
    axes[0].set_ylabel("Frequency", fontsize=11)
    axes[0].set_title(f"{title} - Distribution", fontsize=13, fontweight="bold")
    axes[0].axvline(df[target].mean(), color="red", linestyle="--", label=f"Mean: {df[target].mean():.2f}")
    axes[0].legend()

    # Box plot
    axes[1].boxplot(df[target].dropna(), vert=True, patch_artist=True,
                    boxprops=dict(facecolor="#4f8ef7", alpha=0.7))
    axes[1].set_ylabel(target, fontsize=11)
    axes[1].set_title(f"{title} - Box Plot", fontsize=13, fontweight="bold")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_hourly_pattern(df, target, title, out_path):
    """Average target by hour of day."""
    hourly = df.groupby("hour")[target].mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(hourly.index, hourly.values, color="#4f8ef7", edgecolor="#2563eb", alpha=0.85)
    ax.set_xlabel("Hour of Day", fontsize=11)
    ax.set_ylabel(f"Mean {target}", fontsize=11)
    ax.set_title(f"{title} - Hourly Pattern", fontsize=13, fontweight="bold")
    ax.set_xticks(range(24))
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_weekly_pattern(df, target, title, out_path):
    """Average target by day of week."""
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly = df.groupby("day_of_week")[target].mean().reindex(day_order)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(7), weekly.values, color="#f59e0b", edgecolor="#d97706", alpha=0.85)
    ax.set_xlabel("Day of Week", fontsize=11)
    ax.set_ylabel(f"Mean {target}", fontsize=11)
    ax.set_title(f"{title} - Weekly Pattern", fontsize=13, fontweight="bold")
    ax.set_xticks(range(7))
    ax.set_xticklabels([d[:3] for d in day_order])
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_monthly_trend(df, target, title, out_path):
    """Monthly average trend across the full date range."""
    monthly = df.groupby(df["timestamp"].dt.to_period("M"))[target].mean()
    monthly.index = monthly.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(monthly.index, monthly.values, marker="o", color="#4f8ef7", linewidth=2, markersize=5)
    ax.fill_between(monthly.index, monthly.values, alpha=0.15, color="#4f8ef7")
    ax.set_xlabel("Month", fontsize=11)
    ax.set_ylabel(f"Mean {target}", fontsize=11)
    ax.set_title(f"{title} - Monthly Trend (2024-2025)", fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_heatmap_hour_day(df, target, title, out_path):
    """Heatmap: hour of day vs day of week."""
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = df.pivot_table(values=target, index="hour", columns="day_of_week", aggfunc="mean")
    pivot = pivot.reindex(columns=day_order)

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(pivot, cmap="YlOrRd", annot=False, fmt=".1f", ax=ax,
                xticklabels=[d[:3] for d in day_order])
    ax.set_xlabel("Day of Week", fontsize=11)
    ax.set_ylabel("Hour of Day", fontsize=11)
    ax.set_title(f"{title} - Hour x Day Heatmap", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_correlation_matrix(df, target, title, out_path):
    """Correlation heatmap for numeric columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # Keep only relevant columns (skip IDs that are numeric but not meaningful)
    skip = ["Unnamed"]
    numeric_cols = [c for c in numeric_cols if not any(s in c for s in skip)]

    if len(numeric_cols) > 20:
        # Pick top correlated with target + a few key ones
        corrs = df[numeric_cols].corr()[target].abs().sort_values(ascending=False)
        numeric_cols = corrs.head(15).index.tolist()

    corr = df[numeric_cols].corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, ax=ax, square=True, linewidths=0.5)
    ax.set_title(f"{title} - Correlation Matrix", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_weekend_vs_weekday(df, target, title, out_path):
    """Compare weekend vs weekday distributions."""
    fig, ax = plt.subplots(figsize=(8, 5))

    weekday = df[df["is_weekend"] == 0][target]
    weekend = df[df["is_weekend"] == 1][target]

    ax.hist(weekday, bins=50, alpha=0.6, color="#4f8ef7", label=f"Weekday (mean={weekday.mean():.2f})")
    ax.hist(weekend, bins=50, alpha=0.6, color="#f59e0b", label=f"Weekend (mean={weekend.mean():.2f})")
    ax.set_xlabel(target, fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.set_title(f"{title} - Weekday vs Weekend", fontsize=13, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_summary_stats(df, target, title, out_path):
    """Save a summary statistics table as an image."""
    stats = df[target].describe().round(4)
    stats["missing"] = df[target].isna().sum()
    stats["total_rows"] = len(df)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis("off")
    table_data = [[k, f"{v:,.4f}" if isinstance(v, float) else f"{v:,}"] for k, v in stats.items()]
    table = ax.table(cellText=table_data, colLabels=["Statistic", "Value"],
                     loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)
    ax.set_title(f"{title} - Summary Statistics", fontsize=13, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_eda():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for name, cfg in DATASETS.items():
        print(f"\n{'='*60}")
        print(f"  EDA: {cfg['title']} ({cfg['path']})")
        print(f"{'='*60}")

        df = load_dataset(cfg["path"])
        target = cfg["target"]
        title = cfg["title"]
        prefix = f"{OUTPUT_DIR}/{name}"

        print(f"  Shape: {df.shape}")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Target '{target}': mean={df[target].mean():.4f}, std={df[target].std():.4f}")

        plot_summary_stats(df, target, title, f"{prefix}_summary_stats.png")
        plot_target_distribution(df, target, title, f"{prefix}_distribution.png")
        plot_hourly_pattern(df, target, title, f"{prefix}_hourly_pattern.png")
        plot_weekly_pattern(df, target, title, f"{prefix}_weekly_pattern.png")
        plot_monthly_trend(df, target, title, f"{prefix}_monthly_trend.png")
        plot_heatmap_hour_day(df, target, title, f"{prefix}_heatmap.png")
        plot_correlation_matrix(df, target, title, f"{prefix}_correlation.png")
        plot_weekend_vs_weekday(df, target, title, f"{prefix}_weekend_weekday.png")

    print(f"\n  All EDA charts saved to: {OUTPUT_DIR}/")
    print(f"  Total: {len(DATASETS) * 8} charts generated.")


if __name__ == "__main__":
    run_eda()
