"""Data processing pipeline for Smart Campus Digital Twin."""

from kedro.pipeline import Node, Pipeline

from .nodes import preprocess_canteen, preprocess_energy, preprocess_library


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=preprocess_energy,
                inputs="energy_raw",
                outputs="energy_features",
                name="preprocess_energy_node",
            ),
            Node(
                func=preprocess_canteen,
                inputs="canteen_raw",
                outputs="canteen_features",
                name="preprocess_canteen_node",
            ),
            Node(
                func=preprocess_library,
                inputs="library_raw",
                outputs="library_features",
                name="preprocess_library_node",
            ),
        ]
    )
