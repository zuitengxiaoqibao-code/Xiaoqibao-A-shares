from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from qibao_api.contracts.data_source import DataSourceHealth, NormalizedBatch


class DataSourceAdapter(Protocol):
    source_id: str
    version: str
    priority: int

    def discover(self) -> dict: ...

    def fetch(self, request: dict) -> NormalizedBatch: ...

    def normalize(self, batch) -> NormalizedBatch: ...

    def health(self) -> DataSourceHealth: ...


class DataSourceRegistry:
    def __init__(self, adapters: Iterable[DataSourceAdapter] = ()) -> None:
        self._adapters: dict[str, DataSourceAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: DataSourceAdapter) -> None:
        source_id = str(adapter.source_id).strip()
        if not source_id:
            raise ValueError("数据源标识不能为空")
        if source_id in self._adapters:
            raise ValueError(f"数据源已注册: {source_id}")
        self._adapters[source_id] = adapter

    def get(self, source_id: str) -> DataSourceAdapter:
        try:
            return self._adapters[source_id]
        except KeyError as error:
            raise KeyError(f"数据源未注册: {source_id}") from error

    def discover(self, source_id: str) -> dict:
        return self.get(source_id).discover()

    def health_all(self) -> tuple[DataSourceHealth, ...]:
        return tuple(self._adapters[key].health() for key in sorted(self._adapters))
