"""Data science pipeline for Smart Campus Digital Twin."""

from kedro.pipeline import Node, Pipeline

from .nodes import train_canteen_model, train_energy_model, train_library_model


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=train_energy_model,
                inputs=[
                    "energy_features",
                    "params:energy_model_options",
                    "params:test_size",
                ],
                outputs=["energy_model", "energy_test_predictions"],
                name="train_energy_model_node",
            ),
            Node(
                func=train_canteen_model,
                inputs=[
                    "canteen_features",
                    "params:canteen_model_options",
                    "params:test_size",
                ],
                outputs=["canteen_model", "canteen_test_predictions"],
                name="train_canteen_model_node",
            ),
            Node(
                func=train_library_model,
                inputs=[
                    "library_features",
                    "params:library_model_options",
                    "params:test_size",
                ],
                outputs=["library_model", "library_test_predictions"],
                name="train_library_model_node",
            ),
        ]
    )
