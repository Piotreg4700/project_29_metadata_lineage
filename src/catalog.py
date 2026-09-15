from __future__ import annotations

import hashlib
import json
import platform
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_LOGICAL_TYPES = {
    "object": "string",
    "string": "string",
    "int64": "integer",
    "Int64": "integer",
    "float64": "double",
    "bool": "boolean",
    "datetime64[ns]": "timestamp",
    "datetime64[ns, UTC]": "timestamp",
}


def _logical_type(dtype: str) -> str:
    if dtype.startswith("datetime64"):
        return "timestamp"
    return _LOGICAL_TYPES.get(dtype, dtype)


@dataclass
class ColumnMeta:
    name: str
    dtype: str
    pandas_dtype: str
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
    produced_by_run: str
    created_at: str
    content_hash: str = ""


@dataclass
class Run:
    run_id: str
    step: str
    description: str
    code_ref: str
    inputs: list[str]
    outputs: list[str]
    params: dict[str, Any]
    metrics: dict[str, Any]
    started_at: str
    finished_at: str
    status: str
    environment: dict[str, str]


@dataclass
class LineageEdge:
    src: str
    dst: str
    run_id: str
    kind: str = "dataset"


@dataclass
class ColumnLineageEdge:
    src: str
    dst: str
    run_id: str


class Catalog:
    def __init__(self, pipeline_run_id: str | None = None) -> None:
        self.pipeline_run_id = pipeline_run_id or uuid.uuid4().hex[:12]
        self.created_at = _now()
        self.assets: dict[str, DataAsset] = {}
        self.runs: list[Run] = []
        self.edges: list[LineageEdge] = []
        self.column_edges: list[ColumnLineageEdge] = []

    def start_run(self, step: str, description: str, code_ref: str,
                  inputs: list[str] | None = None,
                  params: dict[str, Any] | None = None) -> Run:
        run = Run(
            run_id=uuid.uuid4().hex[:12],
            step=step,
            description=description,
            code_ref=code_ref,
            inputs=inputs or [],
            outputs=[],
            params=params or {},
            metrics={},
            started_at=_now(),
            finished_at="",
            status="running",
            environment={
                "python": platform.python_version(),
                "platform": platform.platform(),
                "pandas": pd.__version__,
            },
        )
        self.runs.append(run)
        return run

    def finish_run(self, run: Run, status: str = "success",
                   metrics: dict[str, Any] | None = None) -> None:
        run.finished_at = _now()
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

        columns: list[ColumnMeta] = []
        for col in df.columns:
            pdt = str(df[col].dtype)
            columns.append(
                ColumnMeta(
                    name=str(col),
                    dtype=_logical_type(pdt),
                    pandas_dtype=pdt,
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
            produced_by_run=run.run_id,
            created_at=_now(),
            content_hash=self._hash_df(df),
        )
        self.assets[name] = asset
        run.outputs.append(name)

        for src in run.inputs:
            self.edges.append(
                LineageEdge(src=src, dst=name, run_id=run.run_id, kind="dataset")
            )

        for out_col, sources in column_lineage.items():
            for src_ref in sources:
                self.column_edges.append(
                    ColumnLineageEdge(
                        src=src_ref,
                        dst=f"{name}.{out_col}",
                        run_id=run.run_id,
                    )
                )
        return asset

    @staticmethod
    def _hash_df(df: pd.DataFrame) -> str:
        try:
            digest = hashlib.sha256(
                pd.util.hash_pandas_object(df, index=True).values.tobytes()
            ).hexdigest()
            return digest[:16]
        except Exception:
            return ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "created_at": self.created_at,
            "generated_at": _now(),
            "assets": {k: asdict(v) for k, v in self.assets.items()},
            "runs": [asdict(r) for r in self.runs],
            "edges": [asdict(e) for e in self.edges],
            "column_edges": [asdict(e) for e in self.column_edges],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Catalog":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cat = cls(pipeline_run_id=data.get("pipeline_run_id"))
        cat.created_at = data.get("created_at", _now())
        for name, a in data.get("assets", {}).items():
            cols = [ColumnMeta(**c) for c in a.pop("columns", [])]
            cat.assets[name] = DataAsset(columns=cols, **a)
        cat.runs = [Run(**r) for r in data.get("runs", [])]
        cat.edges = [LineageEdge(**e) for e in data.get("edges", [])]
        cat.column_edges = [ColumnLineageEdge(**e) for e in data.get("column_edges", [])]
        return cat

    def downstream_assets(self, asset_name: str) -> list[str]:
        adjacency: dict[str, list[str]] = {}
        for e in self.edges:
            adjacency.setdefault(e.src, []).append(e.dst)
        seen: list[str] = []
        queue = list(adjacency.get(asset_name, []))
        while queue:
            node = queue.pop(0)
            if node not in seen:
                seen.append(node)
                queue.extend(adjacency.get(node, []))
        return seen

    def upstream_assets(self, asset_name: str) -> list[str]:
        adjacency: dict[str, list[str]] = {}
        for e in self.edges:
            adjacency.setdefault(e.dst, []).append(e.src)
        seen: list[str] = []
        queue = list(adjacency.get(asset_name, []))
        while queue:
            node = queue.pop(0)
            if node not in seen:
                seen.append(node)
                queue.extend(adjacency.get(node, []))
        return seen

    def downstream_columns(self, column_ref: str) -> list[str]:
        adjacency: dict[str, list[str]] = {}
        for e in self.column_edges:
            adjacency.setdefault(e.src, []).append(e.dst)
        seen: list[str] = []
        queue = list(adjacency.get(column_ref, []))
        while queue:
            node = queue.pop(0)
            if node not in seen:
                seen.append(node)
                queue.extend(adjacency.get(node, []))
        return seen
