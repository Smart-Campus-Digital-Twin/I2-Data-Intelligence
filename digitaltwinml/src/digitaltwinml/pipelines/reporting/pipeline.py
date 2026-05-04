"""Reporting pipeline for Smart Campus Digital Twin."""

from kedro.pipeline import Node, Pipeline

from .nodes import (
    create_canteen_feature_importance,
    create_energy_feature_importance,
    create_insights_report,
    create_library_feature_importance,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=create_energy_feature_importance,
                inputs="energy_model",
                outputs="energy_feature_importance",
                name="energy_feature_importance_node",
            ),
            Node(
                func=create_canteen_feature_importance,
                inputs="canteen_model",
                outputs="canteen_feature_importance",
                name="canteen_feature_importance_node",
            ),
            Node(
                func=create_library_feature_importance,
                inputs="library_model",
                outputs="library_feature_importance",
                name="library_feature_importance_node",
            ),
            Node(
                func=create_insights_report,
                inputs=[
                    "energy_test_predictions",
                    "canteen_test_predictions",
                    "library_test_predictions",
                ],
                outputs="insights_report",
                name="insights_report_node",
            ),
        ]
    )
