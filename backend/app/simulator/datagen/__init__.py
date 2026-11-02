"""Datagen sub-package. Public entry point: generate(seed=42)."""
from .generator import (
    generate,
    generate_dataset,
    AnomalyKind,
    TransactionRecord,
    write_dataset,
)

__all__ = [
    "generate",
    "generate_dataset",
    "AnomalyKind",
    "TransactionRecord",
    "write_dataset",
]

