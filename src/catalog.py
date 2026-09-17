from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _logical_type(dtype: str) -> str:
    if dtype.startswith("datetime64"):
        return "timestamp"
    return {
        "object": "string",
        "string": "string",
        "int64": "integer",
        "Int64": "integer",
        "float64": "double",
        "bool": "boolean",
    }.get(dtype, dtype)


@dataclass
class ColumnMeta:
    name: str
    dtype: str
    nullable: bool
    null_count: int
    description: str = ""
    source_columns: list[str] = field(default_factory=list)


@dataclass
class DataAsset:
    name: str
    layer: str
    description: str
    location: str
    fmt: str
    row_count: int
    columns: list[ColumnMeta]
    content_hash: str = ""


@dataclass
class Run:
    run_id: str
    step: str
    inputs: list[str]
    outputs: list[str]
    metrics: dict[str, Any]
    status: str


@dataclass
class LineageEdge:
    src: str
    dst: str


@dataclass
class ColumnLineageEdge:
    src: str
    dst: str


def _walk(start: str, pairs: list[tuple[str, str]]) -> list[str]:
    adjacency: dict[str, list[str]] = {}
    for src, dst in pairs:
        adjacency.setdefault(src, []).append(dst)
    seen: list[str] = []
    queue = list(adjacency.get(start, []))
    while queue:
        node = queue.pop(0)
        if node not in seen:
            seen.append(node)
            queue.extend(adjacency.get(node, []))
    return seen


class Catalog:
    def __init__(self) -> None:
        self.pipeline_run_id = uuid.uuid4().hex[:12]
        self.generated_at = _now()
        self.assets: dict[str, DataAsset] = {}
        self.runs: list[Run] = []
        self.edges: list[LineageEdge] = []
        self.column_edges: list[ColumnLineageEdge] = []

    def start_run(self, step: str, inputs: list[str] | None = None) -> Run:
        run = Run(
            run_id=uuid.uuid4().hex[:12],
            step=step,
            inputs=inputs or [],
            outputs=[],
            metrics={},
            status="running",
        )
        self.runs.append(run)
        return run

    def finish_run(self, run: Run, status: str = "success",
                   metrics: dict[str, Any] | None = None) -> None:
        run.status = status
        if metrics:
            run.metrics.update(metrics)

    def register_asset(
        self,
        df: pd.DataFrame,
        *,
        name: str,
        layer: str,
        description: str,
        location: str | Path,
        fmt: str,
        run: Run,
        column_descriptions: dict[str, str] | None = None,
        column_lineage: dict[str, list[str]] | None = None,
    ) -> DataAsset:
        column_descriptions = column_descriptions or {}
        column_lineage = column_lineage or {}

        columns = []
        for col in df.columns:
            pdt = str(df[col].dtype)
            columns.append(
                ColumnMeta(
                    name=str(col),
                    dtype=_logical_type(pdt),
                    nullable=bool(df[col].isna().any()),
                    null_count=int(df[col].isna().sum()),
                    description=column_descriptions.get(col, ""),
                    source_columns=column_lineage.get(col, []),
                )
            )

        asset = DataAsset(
            name=name,
            layer=layer,
            description=description,
            location=str(location),
            fmt=fmt,
            row_count=int(len(df)),
            columns=columns,
            content_hash=self._hash_df(df),
        )
        self.assets[name] = asset
        run.outputs.append(name)

        for src in run.inputs:
            self.edges.append(LineageEdge(src=src, dst=name))
        for out_col, sources in column_lineage.items():
            for src_ref in sources:
                self.column_edges.append(
                    ColumnLineageEdge(src=src_ref, dst=f"{name}.{out_col}")
                )
        return asset

    @staticmethod
    def _hash_df(df: pd.DataFrame) -> str:
        try:
            return hashlib.sha256(
                pd.util.hash_pandas_object(df, index=True).values.tobytes()
            ).hexdigest()[:16]
        except Exception:
            return ""

    def downstream_assets(self, asset_name: str) -> list[str]:
        return _walk(asset_name, [(e.src, e.dst) for e in self.edges])

    def downstream_columns(self, column_ref: str) -> list[str]:
        return _walk(column_ref, [(e.src, e.dst) for e in self.column_edges])
